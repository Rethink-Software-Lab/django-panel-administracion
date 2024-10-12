from inventario.models import Producto, AreaVenta, ProductoInfo
from ..schema import GraficasSchema
from ninja_extra import api_controller, route
from django.utils import timezone
from datetime import timedelta
from django.db.models import F, Sum

from inventario_v2.utils import get_month_name
from ..utils import get_day_name


@api_controller("graficas/", tags=["Gráficas"], permissions=[])
class GraficasController:
    @route.get("", response=GraficasSchema)
    def ventas(self):
        hoy = timezone.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        inicio_mes = hoy.replace(day=1)
        proximo_mes = inicio_mes.replace(day=28) + timedelta(days=4)
        fin_mes = proximo_mes - timedelta(days=proximo_mes.day)
        anno = hoy.year
        mes_actual = hoy.month

        respuestas = {
            "ventasPorArea": [],
            "ventasAnuales": [],
            "masVendidos": [],
            "ventasHoy": 0,
            "ventasSemana": 0,
            "ventasMes": 0,
        }

        # Ventas por área
        areas = AreaVenta.objects.all()
        if areas:
            for dia in range(7):
                dia_fecha = inicio_semana + timedelta(days=dia)
                dia_ventas = {"dia": get_day_name(dia)}
                for area in areas:
                    total_ventas = (
                        Producto.objects.filter(
                            venta__created_at__date=dia_fecha, area_venta=area
                        )
                        .annotate(
                            diferencia=F("info__precio_venta")
                            - F("info__precio_costo")
                            - F("info__pago_trabajador")
                        )
                        .aggregate(total=Sum("diferencia"))
                    )
                    dia_ventas[area.nombre] = {
                        "ventas": total_ventas["total"] if total_ventas["total"] else 0,
                        "color": area.color if area.color else "#000",
                    }
                respuestas["ventasPorArea"].append(dia_ventas)

        # Ventas anuales
        if mes_actual > 0:
            for mes in range(1, mes_actual + 1):
                prod = (
                    Producto.objects.filter(
                        venta__created_at__date__year=anno,
                        venta__created_at__date__month=mes,
                    )
                    .annotate(
                        diferencia=F("info__precio_venta")
                        - F("info__precio_costo")
                        - F("info__pago_trabajador")
                    )
                    .aggregate(total=Sum("diferencia"))
                )
                nombre_mes = get_month_name(mes)
                respuestas["ventasAnuales"].append(
                    {
                        "mes": nombre_mes.capitalize(),
                        "ventas": prod["total"] if prod["total"] else 0,
                    }
                )

        # Ventas hoy
        productos_hoy = (
            Producto.objects.filter(venta__created_at__date=hoy)
            .annotate(
                diferencia=F("info__precio_venta")
                - F("info__precio_costo")
                - F("info__pago_trabajador")
            )
            .aggregate(ventaHoy=Sum("diferencia"))
        )
        respuestas["ventasHoy"] = (
            productos_hoy["ventaHoy"] if productos_hoy["ventaHoy"] else 0
        )

        # Ventas de la semana
        productos_semana = (
            Producto.objects.filter(
                venta__created_at__range=[inicio_semana, fin_semana]
            )
            .annotate(
                diferencia=F("info__precio_venta")
                - F("info__precio_costo")
                - F("info__pago_trabajador")
            )
            .aggregate(ventaSemana=Sum("diferencia"))
        )
        respuestas["ventasSemana"] = (
            productos_semana["ventaSemana"] if productos_semana["ventaSemana"] else 0
        )

        # Ventas del mes
        productos_mes = (
            Producto.objects.filter(venta__created_at__range=[inicio_mes, fin_mes])
            .annotate(
                diferencia=F("info__precio_venta")
                - F("info__precio_costo")
                - F("info__pago_trabajador")
            )
            .aggregate(ventaMes=Sum("diferencia"))
        )
        respuestas["ventasMes"] = (
            productos_mes["ventaMes"] if productos_mes["ventaMes"] else 0
        )

        # Más vendidos
        product_info = ProductoInfo.objects.all()
        products = []

        if product_info:
            for prod_info in product_info:
                productos = Producto.objects.filter(
                    venta__isnull=False, info=prod_info
                ).count()
                if productos < 1:
                    continue
                products.append({"producto": prod_info, "cantidad": productos})

            products.sort(key=lambda producto: producto["cantidad"], reverse=True)
        respuestas["masVendidos"] = products[0:5]

        return respuestas
