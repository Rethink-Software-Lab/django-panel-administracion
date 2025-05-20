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
)
from ..schema import (
    AddEntradaSchema,
    EntradaAlmacenSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from typing import List
from django.db import transaction
from django.db.models import Count, F

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
        cuenta = get_object_or_404(Cuentas, pk=data.cuenta)
        proveedor = get_object_or_404(Proveedor, pk=data.proveedor)

        try:
            with transaction.atomic():
                entrada = EntradaAlmacen(
                    metodo_pago=data.metodoPago,
                    proveedor=proveedor,
                    usuario=user,
                    comprador=data.comprador,
                )
                entrada.save()

                response = []

                for producto in data.productos:
                    producto_info = get_object_or_404(
                        ProductoInfo, pk=producto.producto
                    )
                    print(producto_info.precio_costo)

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

                        cuenta.saldo -= total_zapatos * producto_info.precio_costo
                        cuenta.save()
                        Transacciones.objects.create(
                            entrada=entrada,
                            usuario=user,
                            tipo=TipoTranferenciaChoices.EGRESO,
                            cuenta=cuenta,
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

                        cuenta.saldo -= producto.cantidad * producto_info.precio_costo
                        cuenta.save()
                        Transacciones.objects.create(
                            entrada=entrada,
                            usuario=user,
                            tipo=TipoTranferenciaChoices.EGRESO,
                            cuenta=cuenta,
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

        except Exception as e:
            print(f"Error en la transacción: {str(e)}")
            raise HttpError(400, "Bad Request")

    @route.delete("{id}/")
    def deleteEntrada(self, id: int):

        try:
            with transaction.atomic():
                entrada = get_object_or_404(EntradaAlmacen, pk=id)

                transaccion = get_object_or_404(Transacciones, entrada=entrada)

                cuenta = get_object_or_404(Cuentas, pk=transaccion.cuenta.pk)

                cuenta.saldo += transaccion.cantidad
                cuenta.save()
                transaccion.delete()

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
