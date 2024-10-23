from datetime import datetime
from inventario.models import ProductoInfo, Ventas
from ..schema import VentaReporteSchema
from ninja_extra import api_controller, route
from django.db.models import F, Count, Q, Sum


@api_controller("reportes/", tags=["Categorías"], permissions=[])
class ReportesController:
    @route.get("", response=VentaReporteSchema)
    def getReportes(
        self,
        area: int = 0,
        desde: datetime = datetime.today(),
        hasta: datetime = datetime.today(),
    ):
        parse_desde = desde.date()
        parse_hasta = hasta.date()
        if area:

            producto_info = (
                ProductoInfo.objects.filter(
                    producto__venta__created_at__date__range=(parse_desde, parse_hasta),
                    producto__area_venta_id=area,
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
                created_at__date__range=(parse_desde, parse_hasta), area_venta_id=area
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
            pago_trabajador = (
                producto_info.aggregate(
                    pago_trabajador=Sum(F("pago_trabajador") * F("cantidad"))
                )["pago_trabajador"]
                or 0
            )

            total_costos = pago_trabajador + costo_producto or 0

            return {
                "productos": list(producto_info),
                "subtotal": subtotal,
                "costo_producto": costo_producto,
                "pago_trabajador": pago_trabajador,
                "efectivo": (pagos["efectivo_venta"] or 0)
                + (pagos["efectivo_mixto"] or 0),
                "transferencia": (pagos["transferencia_venta"] or 0)
                + (pagos["transferencia_mixto"] or 0),
                "total": (subtotal - total_costos),
                "area": (
                    producto_info.first()["producto__area_venta__nombre"]
                    if producto_info
                    else None
                ),
            }

        producto_info = (
            ProductoInfo.objects.filter(
                producto__venta__created_at__date__range=(parse_desde, parse_hasta),
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

        ventas = Ventas.objects.filter(
            created_at__date__range=(parse_desde, parse_hasta),
        )

        pagos = ventas.aggregate(
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
        pago_trabajador = (
            producto_info.aggregate(
                pago_trabajador=Sum(F("pago_trabajador") * F("cantidad"))
            )["pago_trabajador"]
            or 0
        )

        total_costos = pago_trabajador + costo_producto or 0

        return {
            "productos": list(producto_info),
            "subtotal": subtotal,
            "costo_producto": costo_producto,
            "pago_trabajador": pago_trabajador,
            "efectivo": (pagos["efectivo_venta"] or 0) + (pagos["efectivo_mixto"] or 0),
            "transferencia": (pagos["transferencia_venta"] or 0)
            + (pagos["transferencia_mixto"] or 0),
            "total": (subtotal - total_costos),
        }
