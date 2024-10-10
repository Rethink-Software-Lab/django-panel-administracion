from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    Producto,
    User,
    Ventas,
    AreaVenta,
    Categorias,
)
from ..schema import (
    AreaVentaSchema,
    OneAreaVentaSchema,
)
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
    def get_one_area_de_venta(self, request, id: int):
        area_venta = get_object_or_404(AreaVenta, id=id)

        producto_info = (
            ProductoInfo.objects.filter(
                producto__venta__isnull=True,
                producto__area_venta=area_venta,
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
            venta__isnull=True, area_venta=area_venta, info__categoria__nombre="Zapatos"
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
            )
            .only("codigo", "categoria")
            .distinct()
        )

        categorias = Categorias.objects.all()

        user = User.objects.get(pk=request.auth["id"])
        if (user.area_venta is None or id != user.area_venta.pk) and not user.is_staff:
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
