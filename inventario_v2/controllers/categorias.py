from ninja.errors import HttpError
from inventario.models import Categorias
from ..schema import CategoriasSchema, CategoriasModifySchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404


@api_controller("categorias/", tags=["Categorías"], permissions=[])
class CategoriasController:
    @route.get("", response=list[CategoriasSchema])
    def getCategorias(self):
        return Categorias.objects.all()

    @route.post("")
    def addCategoria(self, body: CategoriasModifySchema):
        body = body.model_dump()
        try:
            Categorias.objects.create(**body)
            return {"success": True}
        except:
            return HttpError(500, "Error inesperado.")

    @route.put("{id}/")
    def updateCategoria(
        self,
        id: int,
        body: CategoriasModifySchema,
    ):
        body = body.model_dump()
        categoria = get_object_or_404(Categorias, pk=id)
        try:
            categoria.nombre = body["nombre"]
            categoria.save()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")

    @route.delete("{id}/")
    def deleteCategoria(self, id: int):
        categoria = get_object_or_404(Categorias, pk=id)
        try:
            categoria.delete()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")
