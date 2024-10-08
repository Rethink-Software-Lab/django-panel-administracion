from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    EntradaAlmacen,
    Producto,
    SalidaAlmacen,
    User,
    Ventas,
    AreaVenta,
)
from ..schema import AddEntradaSchema, EntradaAlmacenSchema, AreaVentaSchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from typing import List
from django.db import transaction
from django.db.models import Count

from ..custom_permissions import isStaff


@api_controller("areas-ventas/", tags=["Áreas de ventas"], permissions=[isStaff])
class EntradasController:

    @route.get("", response=List[AreaVentaSchema])
    def getAreas(self):
        areas = AreaVenta.objects.all().order_by("-id")
        return areas

    # @route.post("")
    # def addCategoria(self, body: CategoriasModifySchema):
    #     body = body.model_dump()
    #     try:
    #         Categorias.objects.create(**body)
    #         return {"success": True}
    #     except:
    #         return HttpError(500, "Error inesperado.")

    # @route.put("{id}/")
    # def updateCategoria(
    #     self,
    #     id: int,
    #     body: CategoriasModifySchema,
    # ):
    #     body = body.model_dump()
    #     categoria = get_object_or_404(Categorias, pk=id)
    #     try:
    #         categoria.nombre = body["nombre"]
    #         categoria.save()
    #         return {"success": True}
    #     except:
    #         raise HttpError(500, "Error inesperado.")

    # @route.delete("{id}/")
    # def deleteCategoria(self, id: int):
    #     categoria = get_object_or_404(Categorias, pk=id)
    #     try:
    #         categoria.delete()
    #         return {"success": True}
    #     except:
    #         raise HttpError(500, "Error inesperado.")
