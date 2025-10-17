from datetime import datetime
from typing import Literal, Optional

from ninja_extra import api_controller, route

from inventario_v2.controllers.utils_reportes.get_reporte_inventario import get_reporte
from inventario_v2.controllers.utils_reportes.reportes_ventas import get_reporte_ventas
from ..schema import ReportesSchema


@api_controller("reportes/", tags=["Categorías"], permissions=[])
class ReportesController:
    @route.get("", response=ReportesSchema)
    def getReportes(
        self,
        type: Literal["ventas", "inventario"] = "ventas",
        area: Optional[str] = None,
        desde: Optional[datetime] = None,
        hasta: Optional[datetime] = None,
        categoria: Optional[str] = None,
    ):
        final_area = area or "general"
        final_categoria = categoria or "todas"
        parse_desde = (desde or datetime.today()).date()
        parse_hasta = (hasta or datetime.today()).date()

        if type == "ventas":
            response = get_reporte_ventas(parse_desde, parse_hasta, final_area)
            return response

        elif type == "inventario":
            reporte_inventario = get_reporte(final_area, final_categoria)
            return reporte_inventario
