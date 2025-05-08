from decimal import Decimal
from typing import Optional
from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    Ventas,
    User,
    AreaVenta,
    Producto,
    Transacciones,
    TipoTranferenciaChoices,
    METODO_PAGO,
    Cuentas,
)
from ..schema import (
    AddVentaSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction

from ..custom_permissions import isAuthenticated


@api_controller("ventas/", tags=["Ventas"], permissions=[isAuthenticated])
class VentasController:

    @route.post("")
    def addVenta(self, request, data: AddVentaSchema):
        dataDict = data.model_dump()

        area_venta = get_object_or_404(AreaVenta, pk=dataDict["areaVenta"])

        producto_info = get_object_or_404(
            ProductoInfo, codigo=dataDict["producto_info"]
        )
        usuario_search = get_object_or_404(User, pk=request.auth["id"])
        metodo_pago = dataDict["metodoPago"]

        efectivo: Optional[Decimal] = dataDict["efectivo"]
        transferencia: Optional[Decimal] = dataDict["transferencia"]

        cuenta_efectivo = get_object_or_404(Cuentas, pk=25)
        if dataDict["metodoPago"] != METODO_PAGO.EFECTIVO:
            cuenta_transferencia = get_object_or_404(Cuentas, pk=dataDict["tarjeta"])

        if (
            efectivo
            and transferencia
            and producto_info.precio_venta != efectivo + transferencia
        ):
            raise HttpError(
                400, "El importe no coincide con la suma de efectivo y transferencia"
            )

        if producto_info.categoria.nombre == "Zapatos":

            ids_unicos = list(dict.fromkeys(dataDict["zapatos_id"]))

            ids_count = Producto.objects.filter(id__in=ids_unicos).count()

            if ids_count < len(ids_unicos):
                raise HttpError(400, "Algunos ids no existen")

            filtro1 = Producto.objects.filter(pk__in=ids_unicos, info=producto_info)

            if filtro1.count() < len(ids_unicos):
                raise HttpError(400, "Los ids deben ser de un único producto")

            filtro2 = filtro1.filter(venta__isnull=True)

            if filtro2.count() < len(ids_unicos):
                raise HttpError(400, "Algunos productos ya han sido vendidos.")

            productos = filtro2.filter(
                area_venta=area_venta,
                ajusteinventario__isnull=True,
            )

            if productos.count() < len(ids_unicos):
                raise HttpError(400, "Algunos productos no están en el inventario.")

            try:
                with transaction.atomic():
                    venta = Ventas.objects.create(
                        area_venta=area_venta,
                        usuario=usuario_search,
                        metodo_pago=metodo_pago,
                        efectivo=efectivo,
                        transferencia=transferencia,
                    )
                    productos.update(venta=venta)

                    total_venta = ids_count * producto_info.precio_venta

                    if (
                        dataDict["metodoPago"] == METODO_PAGO.MIXTO
                        and transferencia
                        and efectivo
                    ):
                        Transacciones.objects.create(
                            cuenta=cuenta_transferencia,
                            cantidad=transferencia,
                            descripcion=f"[MIXTO] {ids_count}x {dataDict['producto_info']} - {area_venta.nombre}",
                            tipo=TipoTranferenciaChoices.INGRESO,
                            usuario=usuario_search,
                            venta=venta,
                        )
                        cuenta_transferencia.saldo += transferencia
                        cuenta_transferencia.save()
                        Transacciones.objects.create(
                            cuenta=cuenta_efectivo,
                            cantidad=efectivo,
                            descripcion=f"[MIXTO] {ids_count}x {dataDict['producto_info']} - {area_venta.nombre}",
                            tipo=TipoTranferenciaChoices.INGRESO,
                            usuario=usuario_search,
                            venta=venta,
                        )
                        cuenta_efectivo.saldo += efectivo
                        cuenta_efectivo.save()

                    elif dataDict["metodoPago"] == METODO_PAGO.TRANSFERENCIA:
                        Transacciones.objects.create(
                            cuenta=cuenta_transferencia,
                            cantidad=total_venta,
                            descripcion=f"{ids_count}x {dataDict['producto_info']} - {area_venta.nombre}",
                            tipo=TipoTranferenciaChoices.INGRESO,
                            usuario=usuario_search,
                            venta=venta,
                        )
                        cuenta_transferencia.saldo += total_venta
                        cuenta_transferencia.save()

                    else:
                        Transacciones.objects.create(
                            cuenta=cuenta_efectivo,
                            cantidad=total_venta,
                            descripcion=f"{ids_count}x {dataDict['producto_info']} - {area_venta.nombre}",
                            tipo=TipoTranferenciaChoices.INGRESO,
                            usuario=usuario_search,
                            venta=venta,
                        )
                        cuenta_efectivo.saldo += total_venta
                        cuenta_efectivo.save()

                    return {"success": True}
            except Exception as e:
                raise HttpError(500, f"Algo salió mal al agregar la venta. {e}")

        elif dataDict["cantidad"] and dataDict["cantidad"] > 0:

            with transaction.atomic():
                cantidad = dataDict["cantidad"]
                venta = Ventas.objects.create(
                    area_venta=area_venta,
                    usuario=usuario_search,
                    metodo_pago=metodo_pago,
                    efectivo=efectivo,
                    transferencia=transferencia,
                )

                total_venta = cantidad * producto_info.precio_venta

                if (
                    dataDict["metodoPago"] == METODO_PAGO.MIXTO
                    and transferencia
                    and efectivo
                ):
                    Transacciones.objects.create(
                        cuenta=cuenta_transferencia,
                        cantidad=transferencia,
                        descripcion=f"[MIXTO] {cantidad}x {dataDict['producto_info']} - {area_venta.nombre}",
                        tipo=TipoTranferenciaChoices.INGRESO,
                        usuario=usuario_search,
                        venta=venta,
                    )
                    cuenta_transferencia.saldo += transferencia
                    cuenta_transferencia.save()
                    Transacciones.objects.create(
                        cuenta=cuenta_efectivo,
                        cantidad=efectivo,
                        descripcion=f"[MIXTO] {cantidad}x {dataDict['producto_info']} - {area_venta.nombre}",
                        tipo=TipoTranferenciaChoices.INGRESO,
                        usuario=usuario_search,
                        venta=venta,
                    )
                    cuenta_efectivo.saldo += efectivo
                    cuenta_efectivo.save()

                elif dataDict["metodoPago"] == METODO_PAGO.TRANSFERENCIA:
                    Transacciones.objects.create(
                        cuenta=cuenta_transferencia,
                        cantidad=total_venta,
                        descripcion=f"{cantidad}x {dataDict['producto_info']} - {area_venta.nombre}",
                        tipo=TipoTranferenciaChoices.INGRESO,
                        usuario=usuario_search,
                        venta=venta,
                    )
                    cuenta_transferencia.saldo += total_venta
                    cuenta_transferencia.save()

                else:
                    Transacciones.objects.create(
                        cuenta=cuenta_efectivo,
                        cantidad=total_venta,
                        descripcion=f"{cantidad}x {dataDict['producto_info']} - {area_venta.nombre}",
                        tipo=TipoTranferenciaChoices.INGRESO,
                        usuario=usuario_search,
                        venta=venta,
                    )
                    cuenta_efectivo.saldo += total_venta
                    cuenta_efectivo.save()

                productos = Producto.objects.filter(
                    area_venta=area_venta,
                    venta__isnull=True,
                    info=producto_info,
                    ajusteinventario__isnull=True,
                )[:cantidad]

                if productos.count() < cantidad:
                    raise HttpError(
                        400,
                        f"No hay {producto_info.descripcion} suficientes para esta accion",
                    )

                for producto in productos:
                    producto.venta = venta
                    producto.save()

                return {"success": True}

        else:
            raise HttpError(400, "Cantidad requerida en productos != Zapatos")

    @route.delete("{id}/")
    def deleteVenta(self, request, id: int):
        venta = get_object_or_404(Ventas, pk=id)
        user = get_object_or_404(User, pk=request.auth["id"])

        if venta.usuario != user.pk and not user.is_staff:
            raise HttpError(401, "No autorizado.")

        try:
            with transaction.atomic():
                transacciones = Transacciones.objects.filter(venta=venta)
                for transaccion in transacciones:
                    cuenta = Cuentas.objects.get(pk=transaccion.cuenta.pk)
                    cuenta.saldo -= transaccion.cantidad
                    cuenta.save()

                transacciones.delete()
                venta.delete()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")
