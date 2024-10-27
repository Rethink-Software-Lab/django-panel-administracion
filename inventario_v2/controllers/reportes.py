from datetime import datetime
from typing import Literal

from django.shortcuts import get_object_or_404
from inventario.models import ProductoInfo, Ventas, AreaVenta, Salario
from ..schema import ReportesSchema
from ninja_extra import api_controller, route
from django.db.models import F, Count, Q, Sum
from datetime import timedelta


@api_controller("reportes/", tags=["Categorías"], permissions=[])
class ReportesController:
    @route.get("", response=ReportesSchema)
    def getReportes(
        self,
        type: Literal["ventas", "inventario"] = "ventas",
        area: str = "general",
        desde: datetime = datetime.today(),
        hasta: datetime = datetime.today(),
    ):
        parse_desde = desde.date()
        parse_hasta = hasta.date()

        def calcular_dias_laborables(desde, hasta):
            delta = timedelta(days=1)
            dias_laborables = 0
            while desde <= hasta:
                if desde.weekday() != 6:
                    dias_laborables += 1
                desde += delta
            return dias_laborables

        dias_laborables = calcular_dias_laborables(parse_desde, parse_hasta)

        if type == "ventas":
            if area == "general":
                area_venta = "General"
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__venta__created_at__date__range=(
                            parse_desde,
                            parse_hasta,
                        ),
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(
                        cantidad=Count("producto"),
                        importe=F("cantidad") * F("precio_venta"),
                    )
                    .order_by("importe")
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                        "precio_venta",
                        "precio_costo",
                        "importe",
                    )
                )

                ventas_hoy = Ventas.objects.filter(
                    created_at__date__range=(parse_desde, parse_hasta),
                )

            else:
                area_venta = get_object_or_404(AreaVenta, pk=area).nombre

                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__venta__created_at__date__range=(
                            parse_desde,
                            parse_hasta,
                        ),
                        producto__area_venta=area,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(
                        cantidad=Count("producto"),
                        importe=F("cantidad") * F("precio_venta"),
                    )
                    .order_by("importe")
                    .values(
                        "id",
                        "descripcion",
                        "producto__area_venta__nombre",
                        "cantidad",
                        "precio_venta",
                        "precio_costo",
                        "importe",
                    )
                )

                ventas_hoy = Ventas.objects.filter(
                    created_at__date__range=(parse_desde, parse_hasta),
                    area_venta=area,
                )

            pagos = ventas_hoy.aggregate(
                efectivo_venta=Sum(
                    "producto__info__precio_venta", filter=Q(metodo_pago="EFECTIVO")
                ),
                transferencia_venta=Sum(
                    "producto__info__precio_venta",
                    filter=Q(metodo_pago="TRANSFERENCIA"),
                ),
                efectivo_mixto=Sum("efectivo", filter=Q(metodo_pago="MIXTO")),
                transferencia_mixto=Sum("transferencia", filter=Q(metodo_pago="MIXTO")),
            )

            subtotal = producto_info.aggregate(subtotal=Sum("importe"))["subtotal"] or 0
            costo_producto = (
                producto_info.aggregate(
                    costo_producto=Sum(F("precio_costo") * F("cantidad"))
                )["costo_producto"]
                or 0
            )

            all_salarios = (
                Salario.objects.aggregate(salario=Sum("cantidad"))["salario"] or 0
            )

            salarios = all_salarios * dias_laborables

            pago_trabajador = (
                producto_info.aggregate(
                    pago_trabajador=Sum(F("pago_trabajador") * F("cantidad"))
                )["pago_trabajador"]
                or 0
            )

            total_costos = pago_trabajador + costo_producto + salarios or 0

            return {
                "productos": list(producto_info),
                "subtotal": subtotal,
                "costo_producto": costo_producto,
                "salarios": salarios,
                "pago_trabajador": pago_trabajador,
                "efectivo": (pagos["efectivo_venta"] or 0)
                + (pagos["efectivo_mixto"] or 0),
                "transferencia": (pagos["transferencia_venta"] or 0)
                + (pagos["transferencia_mixto"] or 0),
                "total": (subtotal - total_costos),
                "area": area_venta,
            }

        elif type == "inventario":
            if area == "general":
                area_venta = "General"
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__venta__isnull=True,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(cantidad=Count(F("producto")))
                    .exclude(cantidad__lt=1)
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                    )
                )

            elif area == "almacen-principal":
                area_venta = "Almacén Principal"
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__area_venta__isnull=True,
                        producto__almacen_revoltosa=False,
                        producto__venta__isnull=True,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(cantidad=Count(F("producto")))
                    .exclude(cantidad__lt=1)
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                    )
                )

            elif area == "almacen-revoltosa":
                area_venta = "Almacén Revoltosa"
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__area_venta__isnull=True,
                        producto__almacen_revoltosa=True,
                        producto__venta__isnull=True,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(cantidad=Count(F("producto")))
                    .exclude(cantidad__lt=1)
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                    )
                )

            else:
                area_venta = get_object_or_404(AreaVenta, pk=area).nombre
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__area_venta=area,
                        producto__almacen_revoltosa=False,
                        producto__venta__isnull=True,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(cantidad=Count(F("producto")))
                    .exclude(cantidad__lt=1)
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                    )
                )

            return {"productos": producto_info, "area": area_venta}
