from inventario.models import Producto, AreaVenta, ProductoInfo, Salario
from ..schema import GraficasSchema
from ninja_extra import api_controller, route
from django.utils import timezone
from datetime import timedelta
from django.db.models import F, Sum

from inventario_v2.utils import get_month_name
from ..utils import get_day_name

from datetime import datetime
import calendar


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

        salarios = Salario.objects.aggregate(salario=Sum("cantidad"))["salario"] or 0

        def calcular_dias_laborables(desde, hasta):
            delta = timedelta(days=1)
            dias_laborables = 0
            while desde <= hasta:
                if desde.weekday() != 6:
                    dias_laborables += 1
                desde += delta
            return dias_laborables

        def obtener_inicio_fin_mes(anio, mes):
            inicio_mes = datetime(anio, mes, 1)

            ultimo_dia = calendar.monthrange(anio, mes)[1]
            fin_mes = datetime(anio, mes, ultimo_dia)

            return inicio_mes, fin_mes

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
                    if dia_fecha.weekday() != 6:
                        total_ventas_areas = (
                            total_ventas["total"] if total_ventas["total"] else 0
                        ) - salarios
                    else:
                        total_ventas_areas = (
                            total_ventas["total"] if total_ventas["total"] else 0
                        )

                    dia_ventas[area.nombre] = {
                        "ventas": total_ventas_areas,
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
                inicio_mes_graf_anual, fin_mes_graf_anual = obtener_inicio_fin_mes(
                    datetime.now().year, mes
                )

                dias_laborables_graf_anual = calcular_dias_laborables(
                    inicio_mes_graf_anual, fin_mes_graf_anual
                )

                total_mes_graf_anual = salarios * dias_laborables_graf_anual

                nombre_mes = get_month_name(mes)

                respuestas["ventasAnuales"].append(
                    {
                        "mes": nombre_mes.capitalize(),
                        "ventas": (
                            (prod["total"] if prod["total"] else 0)
                            - total_mes_graf_anual
                        ),
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

        if hoy.weekday() != 6:
            total_ventas_hoy = productos_hoy["ventaHoy"] - salarios
        else:
            total_ventas_hoy = (
                productos_hoy["ventaHoy"] if productos_hoy["ventaHoy"] else 0
            )

        respuestas["ventasHoy"] = total_ventas_hoy

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

        total_ventas_semana = (
            productos_semana["ventaSemana"]
            if productos_semana["ventaSemana"]
            else 0 - salarios * calcular_dias_laborables(inicio_semana, fin_semana)
        )

        respuestas["ventasSemana"] = total_ventas_semana

        # Ventas del mes
        productos_mes = (
            Producto.objects.filter(venta__created_at__range=[inicio_mes, fin_mes])
            .annotate(
                diferencia=F("info__precio_venta")
                - F("info__precio_costo")
                - F("info__pago_trabajador")
            )
            .aggregate(ventaMes=Sum("diferencia") or 0)
        )

        salarios_mes = salarios * calcular_dias_laborables(inicio_mes, fin_mes)

        total_ventas_mes = productos_mes["ventaMes"] - salarios_mes

        respuestas["ventasMes"] = total_ventas_mes

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
