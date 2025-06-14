from ninja.errors import HttpError
from inventario.models import (
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
    EntradaAlmacenSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from typing import List
from django.db import transaction
from django.db.models import F

from ..custom_permissions import isStaff


@api_controller("entradas/", tags=["Entradas"], permissions=[isStaff])
class EntradasController:

    @route.get("principal/", response=List[EntradaAlmacenSchema])
    def get_entradas(self):
        from django.utils import timezone
        from datetime import timedelta

        entradas = (
            EntradaAlmacen.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
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
        if data.metodoPago != METODO_PAGO.EFECTIVO:
            cuenta = get_object_or_404(Cuentas, pk=data.cuenta)
        cuenta_efectivo = get_object_or_404(Cuentas, pk=25)
        proveedor = get_object_or_404(Proveedor, pk=data.proveedor)

        with transaction.atomic():
            entrada = EntradaAlmacen(
                metodo_pago=data.metodoPago,
                proveedor=proveedor,
                usuario=user,
                comprador=data.comprador,
            )
            entrada.save()

            response = []

            sum_precio_costo = 0
            for producto in data.productos:
                producto_info = get_object_or_404(ProductoInfo, pk=producto.producto)
                if producto_info.categoria.nombre == 'Zapatos':
                    for variante in producto.variantes:
                        for num in variante.numeros:
                            sum_precio_costo += producto_info.precio_costo * num.cantidad
                else:
                    sum_precio_costo += producto_info.precio_costo * producto.cantidad

            if (
                data.efectivo
                and data.transferencia
                and data.metodoPago == METODO_PAGO.MIXTO
                and data.efectivo + data.transferencia != sum_precio_costo
            ):
                raise HttpError(
                    400,
                    "El total efectivo + transferencia no coincide con el precio de costo",
                )

            if (
                data.metodoPago == METODO_PAGO.EFECTIVO
                and cuenta_efectivo.saldo < sum_precio_costo
            ):
                raise HttpError(
                    400,
                    "No hay saldo suficiente en la cuenta EFECTIVO.",
                )

            if (
                data.metodoPago == METODO_PAGO.TRANSFERENCIA
                and cuenta.saldo < sum_precio_costo
            ):
                raise HttpError(
                    400,
                    f"No hay saldo suficiente en la cuenta {cuenta.nombre}.",
                )

            if (
                data.metodoPago == METODO_PAGO.MIXTO
                and data.transferencia
                and data.efectivo
            ):
                if cuenta.saldo < data.transferencia:
                    raise HttpError(
                        400,
                        f"No hay saldo suficiente en la cuenta {cuenta.nombre}.",
                    )

                if cuenta_efectivo.saldo < data.efectivo:
                    raise HttpError(
                        400,
                        "No hay saldo suficiente en la cuenta EFECTIVO.",
                    )

            for producto in data.productos:
                producto_info = get_object_or_404(ProductoInfo, pk=producto.producto)

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
                            "zapato": producto.producto,
                            "variantes": variantesResponse,
                        }
                    )

                    if (
                        data.metodoPago == METODO_PAGO.MIXTO
                        and data.efectivo
                        and data.transferencia
                    ):
                        cuenta_efectivo.saldo -= data.efectivo
                        cuenta_efectivo.save()

                        cuenta.saldo -= data.transferencia
                        cuenta.save()

                        Transacciones.objects.create(
                            entrada=entrada,
                            usuario=user,
                            tipo=TipoTranferenciaChoices.EGRESO,
                            cuenta=cuenta_efectivo,
                            cantidad=data.efectivo,
                            descripcion=(
                                f"[ENT MIX] {total_zapatos}x {producto_info.descripcion[:34]}..."
                                if len(producto_info.descripcion) > 34
                                else f"[ENT MIX] {total_zapatos}x {producto_info.descripcion}"
                            ),
                        )

                        Transacciones.objects.create(
                            entrada=entrada,
                            usuario=user,
                            tipo=TipoTranferenciaChoices.EGRESO,
                            cuenta=cuenta,
                            cantidad=data.transferencia,
                            descripcion=(
                                f"[ENT MIX] {total_zapatos}x {producto_info.descripcion[:34]}..."
                                if len(producto_info.descripcion) > 34
                                else f"[ENT MIX] {total_zapatos}x {producto_info.descripcion}"
                            ),
                        )
                    else:
                        if data.metodoPago == METODO_PAGO.TRANSFERENCIA:
                            cuenta.saldo -= total_zapatos * producto_info.precio_costo
                            cuenta.save()
                        else:
                            cuenta_efectivo.saldo -= (
                                total_zapatos * producto_info.precio_costo
                            )
                            cuenta_efectivo.save()
                        Transacciones.objects.create(
                            entrada=entrada,
                            usuario=user,
                            tipo=TipoTranferenciaChoices.EGRESO,
                            cuenta=(
                                cuenta
                                if data.metodoPago == METODO_PAGO.TRANSFERENCIA
                                else cuenta_efectivo
                            ),
                            cantidad=total_zapatos * producto_info.precio_costo,
                            descripcion=(
                                f"[ENT] {total_zapatos}x {producto_info.descripcion[:38]}..."
                                if len(producto_info.descripcion) > 38
                                else f"[ENT] {total_zapatos}x {producto_info.descripcion}"
                            ),
                        )

                elif producto.isZapato == False and producto.cantidad:
                    productos = [
                        Producto(
                            info=producto_info,
                            entrada=entrada,
                        )
                        for _ in range(producto.cantidad)
                    ]

                    Producto.objects.bulk_create(productos)

                    if (
                        data.metodoPago == METODO_PAGO.MIXTO
                        and data.efectivo
                        and data.transferencia
                    ):
                        cuenta_efectivo.saldo -= data.efectivo
                        cuenta_efectivo.save()

                        cuenta.saldo -= data.transferencia
                        cuenta.save()

                        Transacciones.objects.create(
                            entrada=entrada,
                            usuario=user,
                            tipo=TipoTranferenciaChoices.EGRESO,
                            cuenta=cuenta_efectivo,
                            cantidad=data.efectivo,
                            descripcion=(
                                f"[ENT MIX] {producto.cantidad}x {producto_info.descripcion[:34]}..."
                                if len(producto_info.descripcion) > 34
                                else f"[ENT MIX] {producto.cantidad}x {producto_info.descripcion}"
                            ),
                        )

                        Transacciones.objects.create(
                            entrada=entrada,
                            usuario=user,
                            tipo=TipoTranferenciaChoices.EGRESO,
                            cuenta=cuenta,
                            cantidad=data.transferencia,
                            descripcion=(
                                f"[ENT MIX] {producto.cantidad}x {producto_info.descripcion[:34]}..."
                                if len(producto_info.descripcion) > 34
                                else f"[ENT MIX] {producto.cantidad}x {producto_info.descripcion}"
                            ),
                        )
                    else:
                        if data.metodoPago == METODO_PAGO.TRANSFERENCIA:
                            cuenta.saldo -= (
                                producto.cantidad * producto_info.precio_costo
                            )
                            cuenta.save()
                        else:
                            cuenta_efectivo.saldo -= (
                                producto.cantidad * producto_info.precio_costo
                            )
                            cuenta_efectivo.save()
                        Transacciones.objects.create(
                            entrada=entrada,
                            usuario=user,
                            tipo=TipoTranferenciaChoices.EGRESO,
                            cuenta=(
                                cuenta
                                if data.metodoPago == METODO_PAGO.TRANSFERENCIA
                                else cuenta_efectivo
                            ),
                            cantidad=producto.cantidad * producto_info.precio_costo,
                            descripcion=(
                                f"[ENT] {producto.cantidad}x {producto_info.descripcion[:38]}..."
                                if len(producto_info.descripcion) > 38
                                else f"[ENT] {producto.cantidad}x {producto_info.descripcion}"
                            ),
                        )

                else:
                    raise HttpError(400, "Bad Request")

            return response

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
