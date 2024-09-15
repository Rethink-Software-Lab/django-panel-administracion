from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    Ventas,
    User,
    AreaVenta,
    Producto,
)
from ..schema import (
    AddVentaSchema,
    VentasSchema,
    VentaReporteSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, F
from datetime import date
from django.db import transaction

from ..custom_permissions import isAuthenticated


@api_controller("ventas/", tags=["Ventas"], permissions=[isAuthenticated])
class VentasController:

    @route.get("{id}/", response=list[VentasSchema])
    def getVenta(self, request, id: int):
        user = User.objects.get(pk=request.auth["id"])
        if id != user.area_venta.id and not user.is_staff:
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

    @route.get("{id}/reporte/", response=VentaReporteSchema)
    def venta_reporte(self, request, id: int):

        user = User.objects.get(pk=request.auth["id"])
        if id != user.area_venta.id and not user.is_staff:
            raise HttpError(401, "Unauthorized")

        producto_info = (
            ProductoInfo.objects.filter(
                producto__venta__created_at__date=date.today(),
                producto__area_venta=id,
            )
            .annotate(cantidad=Count("producto"))
            .annotate(importe=F("cantidad") * F("precio_venta"))
            .order_by("importe")
            .values(
                "id",
                "descripcion",
                "producto__area_venta__nombre",
                "cantidad",
                "precio_venta",
                "importe",
            )
        )
        pago_trabajador = producto_info.aggregate(
            pago_trabajador=Sum("pago_trabajador")
        )["pago_trabajador"]
        subtotal = producto_info.aggregate(subtotal=Sum("importe"))["subtotal"]
        total = subtotal - pago_trabajador if pago_trabajador and subtotal else None
        area = (
            producto_info.first()["producto__area_venta__nombre"]
            if producto_info.first()
            else None
        )

        return {
            "productos": producto_info,
            "subtotal": subtotal,
            "pago_trabajador": pago_trabajador,
            "total": total,
            "area": area,
        }

    @route.post("")
    def addVenta(self, request, data: AddVentaSchema):
        dataDict = data.model_dump()

        area_venta = get_object_or_404(AreaVenta, pk=dataDict["areaVenta"])

        user = User.objects.get(pk=request.auth["id"])

        if user.area_venta != area_venta and not user.is_staff:
            raise HttpError(401, "Unauthorized")

        producto_info = get_object_or_404(
            ProductoInfo, codigo=dataDict["producto_info"]
        )
        usuario_search = get_object_or_404(User, pk=request.auth["id"])
        metodo_pago = dataDict["metodoPago"]

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

            productos = filtro2.filter(area_venta=area_venta)

            if productos.count() < len(ids_unicos):
                raise HttpError(400, "Algunos productos no están en el almacén.")

            try:
                with transaction.atomic():
                    venta = Ventas.objects.create(
                        area_venta=area_venta,
                        usuario=usuario_search,
                        metodo_pago=metodo_pago,
                    )
                    productos.update(venta=venta)

                    return {"success": True}
            except:
                raise HttpError(500, "Algo salió mal al agregar la salida.")

        elif dataDict["cantidad"] and dataDict["cantidad"] > 0:

            with transaction.atomic():
                cantidad = dataDict["cantidad"]
                venta = Ventas.objects.create(
                    area_venta=area_venta,
                    usuario=usuario_search,
                    metodo_pago=metodo_pago,
                )

                productos = Producto.objects.filter(
                    area_venta=area_venta, venta__isnull=True, info=producto_info
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
        if venta.area_venta != user.area_venta and not user.is_staff:
            raise HttpError(401, "Unauthorized")
        try:
            venta.delete()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")
