from inventario.models import (
    ProductoInfo,
    Producto,
    Categorias,
    HistorialPrecioVentaSalon,
)
from ..schema import Almacenes
from ninja_extra import api_controller, route
from django.db.models import F, Count, Q, OuterRef, Subquery
from ..custom_permissions import isAuthenticated


@api_controller("inventario/", tags=["Inventario"], permissions=[isAuthenticated])
class InventarioController:
    @route.get("almacen/", response=Almacenes)
    def getInventarioAlmacen(self):
        ultimo_precio = (
            HistorialPrecioVentaSalon.objects.filter(producto_info=OuterRef("pk"))
            .order_by("-fecha_inicio")
            .values("precio")[:1]
        )
        producto_info = (
            ProductoInfo.objects.select_related("producto", "categoria")
            .filter(
                producto__venta__isnull=True,
                producto__area_venta__isnull=True,
                producto__almacen_revoltosa=False,
                producto__ajusteinventario__isnull=True,
            )
            .annotate(
                cantidad=Count(F("producto")), precio_venta=Subquery(ultimo_precio)
            )
            .exclude(Q(cantidad__lt=1) | Q(categoria__nombre="Zapatos"))
            .values(
                "id",
                "descripcion",
                "cantidad",
                "categoria__nombre",
                "precio_venta",
            )
        )

        zapatos = Producto.objects.filter(
            venta__isnull=True,
            area_venta__isnull=True,
            info__categoria__nombre="Zapatos",
            almacen_revoltosa=False,
            ajusteinventario__isnull=True,
        ).values(
            "id",
            "info__descripcion",
            "color",
            "numero",
        )

        categorias = Categorias.objects.all()

        return {
            "inventario": {"productos": producto_info, "zapatos": zapatos},
            "categorias": categorias,
        }

    @route.get("almacen-revoltosa/", response=Almacenes)
    def getInventarioAlmacenRevoltosa(self):
        ultimo_precio = (
            HistorialPrecioVentaSalon.objects.filter(producto_info=OuterRef("pk"))
            .order_by("-fecha_inicio")
            .values("precio")[:1]
        )

        producto_info = (
            ProductoInfo.objects.select_related("producto", "categoria")
            .filter(
                producto__venta__isnull=True,
                producto__area_venta__isnull=True,
                producto__almacen_revoltosa=True,
                producto__ajusteinventario__isnull=True,
            )
            .annotate(
                cantidad=Count(F("producto")), precio_venta=Subquery(ultimo_precio)
            )
            .exclude(Q(cantidad__lt=1) | Q(categoria__nombre="Zapatos"))
            .values(
                "id",
                "descripcion",
                "cantidad",
                "categoria__nombre",
                "precio_venta",
            )
        )
        zapatos = Producto.objects.filter(
            venta__isnull=True,
            area_venta__isnull=True,
            almacen_revoltosa=True,
            info__categoria__nombre="Zapatos",
            ajusteinventario__isnull=True,
        ).values(
            "id",
            "info__descripcion",
            "color",
            "numero",
        )

        categorias = Categorias.objects.all()

        return {
            "inventario": {"productos": producto_info, "zapatos": zapatos},
            "categorias": categorias,
        }
