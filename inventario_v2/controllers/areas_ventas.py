from ninja.errors import HttpError
from inventario.models import (
    AreaVenta,
)
from ..schema import AreaVentaSchema, AreaVentaModifySchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from typing import List


@api_controller("areas-ventas/", tags=["Áreas de ventas"], permissions=[])
class AreasVentasController:

    @route.get("", response=List[AreaVentaSchema])
    def getAreas(self):
        areas = AreaVenta.objects.all().order_by("-id")
        return areas

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
