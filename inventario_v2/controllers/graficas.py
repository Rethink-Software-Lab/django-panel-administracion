from inventario.models import Producto, AreaVenta
from ninja_extra import api_controller, route
from django.utils import timezone
from datetime import timedelta
from django.db.models import F, Sum

from inventario.utils import get_month_name
from ..utils import get_day_name


@api_controller("graficas/", tags=["Gráficas"], permissions=[])
class GraficasController:
    @route.get("ventas-por-area")
    def ventasPorArea(self):
        hoy = timezone.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday())

        grafico = []

        areas = AreaVenta.objects.all()

        if areas:

            for dia in range(7):  # 0 para lunes, 6 para domingo
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

                grafico.append(dia_ventas)

        return grafico

    @route.get("ventas-anuales")
    def ventasAnuales(self):
        anno = timezone.now().year

        mes_actual = timezone.now().month

        grafico = []
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
                grafico.append(
                    {
                        "mes": nombre_mes.capitalize(),
                        "ventas": prod["total"] if prod["total"] else 0,
                    }
                )
        return grafico

    @route.get("ventas-hoy")
    def ventasHoy(self):
        productos = (
            Producto.objects.filter(venta__created_at__date=timezone.now().date())
            .annotate(
                diferencia=F("info__precio_venta")
                - F("info__precio_costo")
                - F("info__pago_trabajador")
            )
            .aggregate(ventaHoy=Sum("diferencia"))
        )

        return productos["ventaHoy"]

    @route.get("ventas-semana")
    def ventasSemana(self):
        hoy = timezone.now().date()

        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)

        productos = (
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

        return productos["ventaSemana"]

    @route.get("ventas-mes")
    def ventasMes(self):

        today = timezone.now().date()

        inicio_mes = today.replace(day=1)
        proximo_mes = inicio_mes.replace(day=28) + timedelta(
            days=4
        )  # Esto asegura estar en el próximo mes
        fin_mes = proximo_mes - timedelta(days=proximo_mes.day)

        productos = (
            Producto.objects.filter(venta__created_at__range=[inicio_mes, fin_mes])
            .annotate(
                diferencia=F("info__precio_venta")
                - F("info__precio_costo")
                - F("info__pago_trabajador")
            )
            .aggregate(ventaMes=Sum("diferencia"))
        )

        return productos["ventaMes"]
