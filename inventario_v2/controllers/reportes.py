from datetime import datetime

from typing import Literal


from inventario_v2.controllers.utils_reportes.reportes_ventas import get_reporte_ventas
from ..schema import ReportesSchema
from ninja_extra import api_controller, route


from inventario_v2.controllers.utils_reportes.get_reporte_inventario import get_reporte


@api_controller("reportes/", tags=["Categorías"], permissions=[])
class ReportesController:
    @route.get("", response=ReportesSchema)
    def getReportes(
        self,
        type: Literal["ventas", "inventario"] = "ventas",
        area: str = "general",
        desde: datetime = datetime.today(),
        hasta: datetime = datetime.today(),
        categoria: str = "todas",
    ):
        parse_desde = desde.date()
        parse_hasta = hasta.date()

        if type == "ventas":
            response = get_reporte_ventas(parse_desde, parse_hasta, area)
            return response

        elif type == "inventario":
            reporte_inventario = get_reporte(area, categoria)
            return reporte_inventario
