from decimal import Decimal
from itertools import chain
from typing import Annotated, Optional, TypedDict, cast

from django.db.models import F, Count, DecimalField, OuterRef, Subquery, Value
from django.db.models.base import Coalesce
from django.shortcuts import get_object_or_404
from pydantic import Field

from inventario.models import (
    AreaVenta,
    HistorialPrecioVentaCafeteria,
    HistorialPrecioVentaSalon,
    ProductoInfo,
    Productos_Cafeteria,
)


class Productos(TypedDict):
    id: int
    descripcion: str
    cantidad: Annotated[Decimal, Field(gt=0)]
    precio_venta: Annotated[Decimal, Field(gt=0)]


class GetReporte(TypedDict):
    productos: list[Productos]
    area: str


def get_reporte(area: str, categoria: str) -> GetReporte:
    def search_and_format(
        filters: Optional[dict[str, bool | str]] = None,
    ) -> list[Productos]:
        filters = filters.copy() if filters else {}
        if categoria and categoria != "todas":
            filters["categoria__id"] = categoria

        historico_venta = (
            HistorialPrecioVentaSalon.objects.filter(
                producto_info=OuterRef("pk"),
            )
            .order_by("-fecha_inicio")
            .values("precio")[:1]
        )

        productos = (
            ProductoInfo.objects.filter(
                producto__venta__isnull=True,
                producto__ajusteinventario__isnull=True,
                **filters,
            )
            .annotate(
                cantidad=Count("producto"),
                precio_venta=Subquery(historico_venta),
            )
            .exclude(cantidad__lt=1)
            .values(
                "id",
                "descripcion",
                "cantidad",
                "precio_venta",
            )
        )
        return cast(list[Productos], list(productos))

    match area:
        case "general":
            area_venta = "General"
            producto_info_general = search_and_format()

            historico_venta = (
                HistorialPrecioVentaCafeteria.objects.filter(
                    producto=OuterRef("pk"),
                )
                .order_by("-fecha_inicio")
                .values("precio")[:1]
            )

            producto_info_cafeteria = (
                Productos_Cafeteria.objects.annotate(
                    total_cantidad=Coalesce(
                        F("inventario_area__cantidad"),
                        Value(0, output_field=DecimalField()),
                    )
                    + Coalesce(
                        F("inventario_almacen__cantidad"),
                        Value(0, output_field=DecimalField()),
                    ),
                    precio_venta=Subquery(historico_venta),
                )
                .filter(total_cantidad__gt=0)
                .values(
                    "id",
                    "precio_venta",
                    descripcion=F("nombre"),
                    cantidad=F("total_cantidad"),
                )
            )

            producto_info = list(chain(producto_info_general, producto_info_cafeteria))

        case "cafeteria":
            area_venta = "Cafetería"

            historico_venta = (
                HistorialPrecioVentaCafeteria.objects.filter(
                    producto=OuterRef("pk"),
                )
                .order_by("-fecha_inicio")
                .values("precio")[:1]
            )

            producto_info = (
                Productos_Cafeteria.objects.annotate(
                    precio_venta=Subquery(historico_venta),
                )
                .filter(inventario_area__cantidad__gt=0)
                .values(
                    "id",
                    "precio_venta",
                    descripcion=F("nombre"),
                    cantidad=F("inventario_area__cantidad"),
                )
            )
        case "almacen-cafeteria":
            area_venta = "Almacén Cafetería"
            historico_venta = (
                HistorialPrecioVentaCafeteria.objects.filter(
                    producto=OuterRef("pk"),
                )
                .order_by("-fecha_inicio")
                .values("precio")[:1]
            )

            producto_info = (
                Productos_Cafeteria.objects.annotate(
                    precio_venta=Subquery(historico_venta),
                )
                .filter(inventario_almacen__cantidad__gt=0)
                .values(
                    "id",
                    "precio_venta",
                    descripcion=F("nombre"),
                    cantidad=F("inventario_almacen__cantidad"),
                )
            )
        case "almacen-principal":
            area_venta = "Almacén Principal"
            producto_info = search_and_format(
                {
                    "producto__area_venta__isnull": True,
                    "producto__almacen_revoltosa": False,
                }
            )
        case "almacen-revoltosa":
            area_venta = "Almacén Revoltosa"
            producto_info = search_and_format(
                {
                    "producto__area_venta__isnull": True,
                    "producto__almacen_revoltosa": True,
                }
            )
        case _:
            area_obj = get_object_or_404(AreaVenta, pk=area)
            area_venta = area_obj.nombre
            producto_info = search_and_format(
                {"producto__area_venta": area_obj, "producto__almacen_revoltosa": False}
            )

    return {"productos": producto_info, "area": area_venta}
