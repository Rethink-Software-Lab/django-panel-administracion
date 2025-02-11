from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    Ventas,
    User,
    AreaVenta,
    Producto,
    TransferenciasTarjetas,
    TipoTranferenciaChoices,
    METODO_PAGO,
    Tarjetas,
    BalanceTarjetas,
)
from ..schema import (
    AddVentaSchema,
    VentasSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from django.db import transaction

from ..custom_permissions import isAuthenticated


@api_controller("ventas/", tags=["Ventas"], permissions=[isAuthenticated])
class VentasController:

    @route.get("{id}/", response=list[VentasSchema])
    def getVenta(self, request, id: int):
        user = User.objects.get(pk=request.auth["id"])

        is_authorized = False

        if user.is_staff:
            is_authorized = True

        elif user.area_venta is not None:
            if id == 28:
                if (
                    user.area_venta.pk == 4
                    or user.area_venta.pk == 6
                    or user.area_venta.pk == 25
                    or user.area_venta.pk == 17
                    or user.area_venta.pk == id
                ):
                    is_authorized = True

            elif id == 27:
                if user.area_venta.pk == 17 or user.area_venta.pk == id:
                    is_authorized = True
            else:
                if id == user.area_venta.pk:
                    is_authorized = True

        if not is_authorized:
            raise HttpError(401, "Unauthorized")
        ventas = (
            Ventas.objects.filter(area_venta=id)
            .annotate(
                importe=Sum("producto__info__precio_venta")
                - Sum("producto__info__pago_trabajador"),
                cantidad=Count("producto"),
            )
            .values(
                "importe",
                "created_at",
                "metodo_pago",
                "usuario__username",
                "producto__info__descripcion",
                "cantidad",
                "id",
            )
            .order_by("-created_at")
        )
        return ventas

    @route.post("")
    def addVenta(self, request, data: AddVentaSchema):
        dataDict = data.model_dump()

        area_venta = get_object_or_404(AreaVenta, pk=dataDict["areaVenta"])

        user = User.objects.get(pk=request.auth["id"])

        is_authorized = False

        if user.is_staff:
            is_authorized = True
        elif user.area_venta is not None:
            if area_venta.pk == 28:
                if (
                    user.area_venta.pk == 4
                    or user.area_venta.pk == 6
                    or user.area_venta.pk == 25
                    or user.area_venta.pk == 17
                    or user.area_venta.pk == area_venta.pk
                ):
                    is_authorized = True
            elif area_venta.pk == 27:
                if user.area_venta.pk == 17 or user.area_venta.pk == area_venta.pk:
                    is_authorized = True
            else:
                if area_venta.pk == user.area_venta.pk:
                    is_authorized = True

        if not is_authorized:
            raise HttpError(401, "Unauthorized")

        producto_info = get_object_or_404(
            ProductoInfo, codigo=dataDict["producto_info"]
        )
        usuario_search = get_object_or_404(User, pk=request.auth["id"])
        metodo_pago = dataDict["metodoPago"]

        efectivo = dataDict["efectivo"] if metodo_pago == "MIXTO" else None
        transferencia = dataDict["transferencia"] if metodo_pago == "MIXTO" else None

        if metodo_pago == METODO_PAGO.MIXTO or metodo_pago == METODO_PAGO.TRANSFERENCIA:
            tarjeta = get_object_or_404(Tarjetas, pk=dataDict["tarjeta"])

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

                    if (
                        metodo_pago == METODO_PAGO.MIXTO
                        or metodo_pago == METODO_PAGO.TRANSFERENCIA
                    ):
                        if metodo_pago == METODO_PAGO.MIXTO:
                            if transferencia is None:
                                raise HttpError(400, "transferencia es requerida")
                            cantidad = (
                                ids_count * transferencia if transferencia else None
                            )
                            decripcion = f"[MIXTO] {ids_count}x {dataDict['producto_info']} - {area_venta.nombre}"
                            sumar_al_balance = transferencia

                        elif metodo_pago == METODO_PAGO.TRANSFERENCIA:
                            cantidad = ids_count * producto_info.precio_venta
                            decripcion = f"{ids_count}x {dataDict['producto_info']} - {area_venta.nombre}"
                            sumar_al_balance = ids_count * producto_info.precio_venta

                        TransferenciasTarjetas.objects.create(
                            tarjeta=tarjeta,
                            cantidad=cantidad,
                            descripcion=decripcion,
                            tipo=TipoTranferenciaChoices.INGRESO,
                            usuario=usuario_search,
                            venta=venta,
                        )
                        balance = BalanceTarjetas.objects.get(tarjeta=tarjeta)
                        balance.valor = balance.valor + sumar_al_balance
                        balance.save()

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

                if (
                    metodo_pago == METODO_PAGO.MIXTO
                    or metodo_pago == METODO_PAGO.TRANSFERENCIA
                ):
                    TransferenciasTarjetas.objects.create(
                        tarjeta=tarjeta,
                        cantidad=dataDict["cantidad"] * producto_info.precio_venta,
                        descripcion=f"{dataDict["cantidad"]}x {dataDict["producto_info"]} - {area_venta.nombre}",
                        tipo=TipoTranferenciaChoices.INGRESO,
                        usuario=usuario_search,
                        venta=venta,
                    )
                    balance = BalanceTarjetas.objects.get(tarjeta=tarjeta)
                    balance.valor = balance.valor + (
                        dataDict["cantidad"] * producto_info.precio_venta
                    )
                    balance.save()

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
        user = User.objects.get(pk=request.auth["id"])

        is_authorized = False

        if user.is_staff:
            is_authorized = True
        elif user.area_venta is not None:
            if venta.area_venta.pk == 28:
                if (
                    user.area_venta.pk == 4
                    or user.area_venta.pk == 6
                    or user.area_venta.pk == 25
                    or user.area_venta.pk == 17
                    or user.area_venta.pk == venta.area_venta.pk
                ):
                    is_authorized = True
            elif venta.area_venta.pk == 27:
                if (
                    user.area_venta.pk == 17
                    or user.area_venta.pk == venta.area_venta.pk
                ):
                    is_authorized = True
            else:
                if venta.area_venta.pk == user.area_venta.pk:
                    is_authorized = True

        if not is_authorized:
            raise HttpError(401, "Unauthorized")
        try:
            with transaction.atomic():
                if venta.metodo_pago != METODO_PAGO.EFECTIVO:
                    transferencia = get_object_or_404(
                        TransferenciasTarjetas, venta=venta
                    )
                    balance = BalanceTarjetas.objects.get(tarjeta=transferencia.tarjeta)

                    balance.valor = balance.valor - transferencia.cantidad
                    balance.save()

                venta.delete()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")
