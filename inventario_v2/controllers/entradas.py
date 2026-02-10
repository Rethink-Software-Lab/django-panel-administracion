from decimal import Decimal
from typing import List, Tuple
from django.db.models import F
from ninja.errors import HttpError
from inventario.models import (
    CuentasChoices,
    ProductoInfo,
    EntradaAlmacen,
    Producto,
    Proveedor,
    SalidaAlmacen,
    SalidaAlmacenRevoltosa,
    User,
    Ventas,
    Transacciones,
    TipoTranferenciaChoices,
    Cuentas,
    METODO_PAGO,
)
from ..schema import (
    AddEntradaSchema,
    CuentasInCreateEntrada,
    EntradaAlmacenSchema,
    ProductosEntradaAlmacenPrincipal,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction

from ..custom_permissions import isStaff


def sumatoria_precio_costo(
    productos: List[ProductosEntradaAlmacenPrincipal],
) -> Tuple[int, int]:
    sum_precio_costo = 0
    cantidad_productos = 0
    for producto in productos:
        producto_info = get_object_or_404(ProductoInfo, pk=producto.producto)

        # Cambiar localizacion del producto
        if producto.localizacion.__len__() > 0:
            producto_info.localizacion = producto.localizacion
            producto_info.save()
   
        if producto_info.categoria.nombre == "Zapatos":
            if not producto.variantes:
                continue
            for variante in producto.variantes:
                for num in variante.numeros:
                    sum_precio_costo += producto_info.precio_costo * num.cantidad
                    cantidad_productos += num.cantidad
        else:
            sum_precio_costo += producto_info.precio_costo * producto.cantidad
            cantidad_productos += producto.cantidad or 0
    return sum_precio_costo, cantidad_productos


def is_valid_cuenta(cuenta: Cuentas, metodo_pago: str) -> HttpError | None:
    if (
        metodo_pago == METODO_PAGO.EFECTIVO and cuenta.tipo != CuentasChoices.EFECTIVO
    ) or (
        metodo_pago == METODO_PAGO.TRANSFERENCIA
        and (cuenta.tipo != CuentasChoices.BANCARIA and cuenta.tipo != CuentasChoices.ZELLE)
    ):
        raise HttpError(400, "Cuenta no válida para el método de pago.")


def saldo_suficiente_cuenta(
    cuenta: Cuentas, saldo_a_rebajar: Decimal
) -> HttpError | None:
    if cuenta.saldo < saldo_a_rebajar:
        raise HttpError(400, f"Saldo insuficiente en la cuenta: {cuenta.nombre}.")


def procesar_rebajas_cuentas(
    cuentas: List[CuentasInCreateEntrada], metodo_pago: str, sum_precio_costo: Decimal
) -> HttpError | None:
    if cuentas.count == 1 and metodo_pago == METODO_PAGO.MIXTO:
        raise HttpError(400, "El método de pago es MIXTO requiere al menos 2 cuentas")

    sum_cantidad_en_cuentas = Decimal(0)
    for cuenta in cuentas:
        cuentaQS = get_object_or_404(Cuentas, pk=cuenta.cuenta)
        is_valid_cuenta(cuentaQS, metodo_pago)
        saldo_suficiente_cuenta(cuentaQS, Decimal(cuenta.cantidad or 0))
        sum_cantidad_en_cuentas += Decimal(cuenta.cantidad or 0)

    if sum_cantidad_en_cuentas != sum_precio_costo:
        raise HttpError(
            400,
            "El total de las cantidades de las cuentas no coincide con el precio de costo.",
        )


def rebajar_saldo(cuentas: List[CuentasInCreateEntrada]) -> None:
    for cuenta in cuentas:
        cuentaQS = get_object_or_404(Cuentas, pk=cuenta.cuenta)
        cuentaQS.saldo -= Decimal(cuenta.cantidad or 0)
        cuentaQS.save()


def crear_transacciones(
    entrada: EntradaAlmacen,
    cuentas: List[CuentasInCreateEntrada],
    usuario: User,
    cantidad_productos: int,
) -> None:
    for cuenta in cuentas:
        cuentaQS = get_object_or_404(Cuentas, pk=cuenta.cuenta)
        Transacciones.objects.create(
            entrada=entrada,
            usuario=usuario,
            tipo=TipoTranferenciaChoices.ENTRADA,
            cuenta=cuentaQS,
            saldo_resultante=cuentaQS.saldo,
            cantidad=Decimal(cuenta.cantidad or 0),
            descripcion=f"{cantidad_productos} Productos - Almacén Principal",
        )


@api_controller("entradas/", tags=["Entradas"], permissions=[isStaff])
class EntradasController:
    @route.get("principal/", response=List[EntradaAlmacenSchema])
    def get_entradas(self):
        from django.utils import timezone
        from datetime import timedelta

        entradas = (
            EntradaAlmacen.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=60)
            )
            .annotate(
                username=F("usuario__username"),
                fecha=F("created_at"),
                nombre_proveedor=F("proveedor__nombre"),
            )
            .values(
                "id",
                "metodo_pago",
                "nombre_proveedor",
                "comprador",
                "username",
                "fecha",
            )
            .order_by("-fecha")
        )
        return entradas

    @route.post("")
    def addEntrada(self, request, data: AddEntradaSchema):
        user = get_object_or_404(User, pk=request.auth["id"])
        proveedor = get_object_or_404(Proveedor, pk=data.proveedor)
        response = []
        sum_precio_costo, cantidad_productos = sumatoria_precio_costo(data.productos)

        if len(data.cuentas) == 1:
            data.cuentas[0].cantidad = Decimal(sum_precio_costo)

        procesar_rebajas_cuentas(
            data.cuentas, data.metodoPago, Decimal(sum_precio_costo)
        )

        try:
            with transaction.atomic():
                entrada = EntradaAlmacen(
                    metodo_pago=data.metodoPago,
                    proveedor=proveedor,
                    usuario=user,
                    comprador=data.comprador,
                )
                entrada.save()

                rebajar_saldo(data.cuentas)

                crear_transacciones(entrada, data.cuentas, user, cantidad_productos)

                for producto in data.productos:
                    producto_info = get_object_or_404(
                        ProductoInfo, pk=producto.producto
                    )

                    variantesResponse = []

                    if producto.isZapato and producto.variantes:
                        total_zapatos = 0

                        for variante in producto.variantes:
                            productos_pa = []

                            for num in variante.numeros:
                                ids = []

                                productos = [
                                    Producto(
                                        info=producto_info,
                                        color=variante.color,
                                        numero=num.numero,
                                        entrada=entrada,
                                    )
                                    for _ in range(num.cantidad)
                                ]

                                total_zapatos += num.cantidad

                                ids = Producto.objects.bulk_create(productos)

                                formated_ids = (
                                    f"{ids[0].pk}-{ids[-1].pk}"
                                    if len(ids) > 1
                                    else ids[0].pk
                                )
                                productos_pa.append(
                                    {"numero": num.numero, "ids": formated_ids}
                                )

                            variantesResponse.append(
                                {"color": variante.color, "numeros": productos_pa}
                            )
                        response.append(
                            {
                                "zapato": producto_info.descripcion,
                                "variantes": variantesResponse,
                            }
                        )

                    elif not producto.isZapato and producto.cantidad:
                        productos = [
                            Producto(
                                info=producto_info,
                                entrada=entrada,
                            )
                            for _ in range(producto.cantidad)
                        ]

                        Producto.objects.bulk_create(productos)
            return response

        except Exception as err:
            print(err)
            raise HttpError(500, "Error al crear la entrada.")

    @route.delete("{id}/")
    def deleteEntrada(self, id: int):
        try:
            with transaction.atomic():
                entrada = get_object_or_404(EntradaAlmacen, pk=id)

                transacciones = Transacciones.objects.filter(entrada=entrada)

                for transaccion in transacciones:
                    cuenta = get_object_or_404(Cuentas, pk=transaccion.cuenta.pk)

                    cuenta.saldo += transaccion.cantidad
                    cuenta.save()

                transacciones.delete()

                productos_ids = Producto.objects.filter(entrada=entrada).values_list(
                    "id", flat=True
                )

                salidas = SalidaAlmacen.objects.filter(
                    producto__id__in=productos_ids
                ).distinct()

                salidas_revoltosa = SalidaAlmacenRevoltosa.objects.filter(
                    producto__id__in=productos_ids
                ).distinct()

                ventas = Ventas.objects.filter(
                    producto__id__in=productos_ids
                ).distinct()

                ventas.delete()
                salidas.delete()
                salidas_revoltosa.delete()
                entrada.delete()
        except Exception as e:
            raise HttpError(400, f"Error al eliminar la entrada: {str(e)}")
