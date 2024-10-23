from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    Producto,
    Ventas,
    AreaVenta,
    Categorias,
)
from ..schema import AreaVentaSchema, OneAreaVentaSchema, AreaVentaModifySchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from typing import List
from django.db.models import Count, Q, F, Sum


@api_controller("areas-ventas/", tags=["Áreas de ventas"], permissions=[])
class AreasVentasController:

    @route.get("", response=List[AreaVentaSchema])
    def getAreas(self):
        areas = AreaVenta.objects.all().order_by("-id")
        return areas

    @route.get("{id}/", response=OneAreaVentaSchema)
    def get_one_area_de_venta(self, id: int):
        area_venta = get_object_or_404(AreaVenta, id=id)

        producto_info = (
            ProductoInfo.objects.filter(
                producto__venta__isnull=True,
                producto__area_venta=area_venta,
                producto__ajusteinventario__isnull=True,
            )
            .annotate(cantidad=Count(F("producto")))
            .exclude(Q(cantidad__lt=1) | Q(categoria__nombre="Zapatos"))
            .values(
                "id",
                "descripcion",
                "codigo",
                "precio_venta",
                "cantidad",
                "categoria__nombre",
            )
        )
        zapatos = Producto.objects.filter(
            venta__isnull=True,
            area_venta=area_venta,
            info__categoria__nombre="Zapatos",
            ajusteinventario__isnull=True,
        ).values(
            "id",
            "info__codigo",
            "info__descripcion",
            "color",
            "numero",
        )

        all_productos = (
            ProductoInfo.objects.filter(
                producto__venta__isnull=True,
                producto__area_venta=area_venta,
                producto__ajusteinventario__isnull=True,
            )
            .only("codigo", "categoria")
            .distinct()
        )

        categorias = Categorias.objects.all()

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
        return {
            "inventario": {
                "productos": producto_info,
                "zapatos": zapatos,
                "categorias": categorias,
            },
            "ventas": ventas,
            "area_venta": area_venta.nombre,
            "all_productos": all_productos,
        }

    @route.post("", response=None)
    def addArea(self, area: AreaVentaModifySchema):
        new_area = area.model_dump()
        try:
            AreaVenta.objects.create(**new_area)
            return
        except:
            return HttpError(500, "Error inesperado.")

    @route.put("{id}/")
    def updateArea(
        self,
        id: int,
        area: AreaVentaModifySchema,
    ):
        new_area = area.model_dump()
        area_to_edit = get_object_or_404(AreaVenta, pk=id)
        try:
            area_to_edit.nombre = new_area["nombre"]
            area_to_edit.color = new_area["color"]
            area_to_edit.save()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")

    @route.delete("{id}/", response=None)
    def delete_area_de_venta(self, id: int):
        area = get_object_or_404(AreaVenta, pk=id)
        try:
            area.delete()
            return
        except:
            raise HttpError(500, "Error inesperado.")
