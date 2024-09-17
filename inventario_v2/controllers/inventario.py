from inventario.models import AreaVenta, ProductoInfo, Producto
from ..schema import InventarioSchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db.models import F, Count, Q
from ..custom_permissions import isAuthenticated


@api_controller("inventario/", tags=["Inventario"], permissions=[isAuthenticated])
class InventarioController:

    @route.get("almacen/", response=InventarioSchema)
    def getInventarioAlmacen(self):
        producto_info = (
            ProductoInfo.objects.filter(
                producto__venta__isnull=True,
                producto__area_venta__isnull=True,
            )
            .annotate(cantidad=Count(F("producto")))
            .exclude(Q(cantidad__lt=1) | Q(categoria__nombre="Zapatos"))
            .values(
                "id",
                "descripcion",
                "codigo",
                "cantidad",
                "categoria__nombre",
                "precio_venta",
            )
        )
        zapatos = Producto.objects.filter(
            venta__isnull=True,
            area_venta__isnull=True,
            info__categoria__nombre="Zapatos",
        )
        return {"productos": producto_info, "zapatos": zapatos}

    @route.get("area-venta/{id}/", response=InventarioSchema)
    def getInventarioAreaVenta(self, id: int):
        area_venta = get_object_or_404(AreaVenta, pk=id)
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
        )

        return {"productos": producto_info, "zapatos": zapatos}
