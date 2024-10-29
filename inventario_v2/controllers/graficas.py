from inventario.models import (
    Producto,
    AreaVenta,
    ProductoInfo,
    Gastos,
    GastosChoices,
    FrecuenciaChoices,
)
from ..schema import GraficasSchema
from ninja_extra import api_controller, route
from django.utils import timezone
from datetime import timedelta
from django.db.models import F, Sum, Case, When, IntegerField

from inventario_v2.utils import get_month_name
from ..utils import (
    get_day_name,
    # calcular_dias_laborables,
    obtener_inicio_fin_mes,
    obtener_ultimo_dia_mes,
    obtener_dias_semana_rango,
)

from datetime import datetime


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
        gastos_variables = Gastos.objects.filter(tipo=GastosChoices.VARIABLE)
        gastos_fijos = Gastos.objects.filter(
            tipo=GastosChoices.FIJO, created_at__date__gte=inicio_mes
        )

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
                        .aggregate(total=Sum("diferencia"))["total"]
                        or 0
                    )

                    dia_ventas[area.nombre] = {
                        "ventas": total_ventas,
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

                gastos_variables__graf_anual = (
                    gastos_variables.filter(
                        created_at__date__range=(
                            inicio_mes_graf_anual,
                            fin_mes_graf_anual,
                        ),
                    ).aggregate(total=Sum("cantidad"))["total"]
                    or 0
                )

                ultimo_dia_hasta = obtener_ultimo_dia_mes(fin_mes_graf_anual)

                gastos_fijos_mes_optimizado_graf_anual = gastos_fijos.filter(
                    frecuencia=FrecuenciaChoices.MENSUAL,
                ).annotate(
                    dia_mes_ajustado=Case(
                        When(dia_mes__gt=ultimo_dia_hasta, then=ultimo_dia_hasta),
                        default=F("dia_mes"),
                        output_field=IntegerField(),
                    )
                )

                gastos_fijos_mesuales_graf_anual = (
                    gastos_fijos_mes_optimizado_graf_anual.filter(
                        dia_mes_ajustado__range=(
                            inicio_mes_graf_anual.day,
                            fin_mes_graf_anual.day + 1,
                        )
                    ).aggregate(total=Sum("cantidad"))["total"]
                    or 0
                )

                dias_semana_graf_anual = obtener_dias_semana_rango(
                    inicio_mes_graf_anual, fin_mes_graf_anual
                )

                filter_gastos_fijos_semanales_graf_anual = gastos_fijos.filter(
                    frecuencia=FrecuenciaChoices.SEMANAL,
                    dia_semana__in=dias_semana_graf_anual,
                )

                gastos_fijos_semanales_graf_anual = (
                    sum(
                        gasto.cantidad * dias_semana_graf_anual.get(gasto.dia_semana, 0)
                        for gasto in filter_gastos_fijos_semanales_graf_anual
                    )
                    or 0
                )

                total_gastos_graf_anual = (
                    gastos_variables__graf_anual
                    + gastos_fijos_mesuales_graf_anual
                    + gastos_fijos_semanales_graf_anual
                )

                nombre_mes = get_month_name(mes)

                respuestas["ventasAnuales"].append(
                    {
                        "mes": nombre_mes.capitalize(),
                        "ventas": (
                            (prod["total"] if prod["total"] else 0)
                            - total_gastos_graf_anual
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
            .aggregate(ventaHoy=Sum("diferencia"))["ventaHoy"]
        ) or 0

        gastos_variables_hoy = (
            gastos_variables.filter(created_at=hoy).aggregate(total=Sum("cantidad"))[
                "total"
            ]
            or 0
        )
        gastos_fijos_mesuales_hoy = (
            gastos_fijos.filter(
                frecuencia=FrecuenciaChoices.MENSUAL,
                dia_mes=hoy.day,
            ).aggregate(total=Sum("cantidad"))["total"]
            or 0
        )

        gastos_fijos_semanales_hoy = (
            gastos_fijos.filter(
                frecuencia=FrecuenciaChoices.SEMANAL,
                dia_semana=hoy.weekday(),
            ).aggregate(total=Sum("cantidad"))["total"]
            or 0
        )

        total_gastos_hoy = (
            gastos_variables_hoy
            + gastos_fijos_mesuales_hoy
            + gastos_fijos_semanales_hoy
        )

        total_ventas_hoy = productos_hoy - total_gastos_hoy

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
            .aggregate(ventaSemana=Sum("diferencia"))["ventaSemana"]
            or 0
        )

        gastos_variables_semana = (
            gastos_variables.filter(
                created_at__range=[inicio_semana, fin_semana],
            ).aggregate(total=Sum("cantidad"))["total"]
            or 0
        )

        gastos_fijos_mesuales_semana = (
            gastos_fijos.filter(
                frecuencia=FrecuenciaChoices.MENSUAL,
                dia_semana__range=[inicio_semana.day, fin_semana.day],
            ).aggregate(total=Sum("cantidad"))["total"]
            or 0
        )

        gastos_fijos_semanales_semana = (
            gastos_fijos.filter(
                frecuencia=FrecuenciaChoices.SEMANAL,
            ).aggregate(
                total=Sum("cantidad")
            )["total"]
            or 0
        )

        total_gastos_semana = (
            gastos_variables_semana
            + gastos_fijos_mesuales_semana
            + gastos_fijos_semanales_semana
        )

        total_ventas_semana = productos_semana - total_gastos_semana

        respuestas["ventasSemana"] = total_ventas_semana

        # Ventas del mes
        productos_mes = (
            Producto.objects.filter(venta__created_at__range=[inicio_mes, fin_mes])
            .annotate(
                diferencia=F("info__precio_venta")
                - F("info__precio_costo")
                - F("info__pago_trabajador")
            )
            .aggregate(ventaMes=Sum("diferencia"))["ventaMes"]
            or 0
        )

        gastos_variables_mes = (
            gastos_variables.filter(created_at__range=[inicio_mes, fin_mes]).aggregate(
                total=Sum("cantidad")
            )["total"]
            or 0
        )

        ultimo_dia_hasta = obtener_ultimo_dia_mes(fin_mes)

        gastos_fijos_mes_optimizado = gastos_fijos.filter(
            frecuencia=FrecuenciaChoices.MENSUAL,
        ).annotate(
            dia_mes_ajustado=Case(
                When(dia_mes__gt=ultimo_dia_hasta, then=ultimo_dia_hasta),
                default=F("dia_mes"),
                output_field=IntegerField(),
            )
        )

        gastos_fijos_mesuales_mes = (
            gastos_fijos_mes_optimizado.filter(
                dia_mes_ajustado__range=(inicio_mes.day, fin_mes.day + 1)
            ).aggregate(total=Sum("cantidad"))["total"]
            or 0
        )

        dias_semana = obtener_dias_semana_rango(inicio_mes, fin_mes)

        filter_gastos_fijos_semanales_mes = gastos_fijos.filter(
            frecuencia=FrecuenciaChoices.SEMANAL,
            dia_semana__in=dias_semana,
        )

        gastos_fijos_semanales_mes = (
            sum(
                gasto.cantidad * dias_semana.get(gasto.dia_semana, 0)
                for gasto in filter_gastos_fijos_semanales_mes
            )
            or 0
        )

        total_gastos_mes = (
            gastos_variables_mes
            + gastos_fijos_mesuales_mes
            + gastos_fijos_semanales_mes
        )

        total_ventas_mes = productos_mes - total_gastos_mes

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
