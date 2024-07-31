from inventario.models import Producto, AreaVenta
from ninja_extra import api_controller, route
from django.utils import timezone
from datetime import timedelta
from django.db.models import F, Sum
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
                            diferencia=F("info__precio_venta") - F("info__precio_costo")
                        )
                        .aggregate(total=Sum("diferencia"))
                    )
                    dia_ventas[area.nombre] = {
                        "ventas": total_ventas["total"] if total_ventas["total"] else 0,
                        "color": area.color if area.color else "#000",
                    }

                grafico.append(dia_ventas)

        return grafico
