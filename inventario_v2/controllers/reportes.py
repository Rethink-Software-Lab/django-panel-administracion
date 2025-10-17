from datetime import datetime
from typing import Literal, Optional

from ninja import Schema, Query
from pydantic import field_validator
from ninja_extra import api_controller, route

from inventario_v2.controllers.utils_reportes.get_reporte_inventario import get_reporte
from inventario_v2.controllers.utils_reportes.reportes_ventas import get_reporte_ventas
from ..schema import ReportesSchema


class ReportesInput(Schema):
    type: Literal["ventas", "inventario"] = "ventas"
    area: Optional[str] = None
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
    categoria: Optional[str] = None

    @field_validator("area", "categoria", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v


@api_controller("reportes/", tags=["Categorías"], permissions=[])
class ReportesController:
    @route.get("", response=ReportesSchema)
    def getReportes(self, filters: ReportesInput = Query(...)):
        final_area = filters.area or "general"
        final_categoria = filters.categoria or "todas"
        parse_desde = (filters.desde or datetime.today()).date()
        parse_hasta = (filters.hasta or datetime.today()).date()

        if filters.type == "ventas":
            response = get_reporte_ventas(parse_desde, parse_hasta, final_area)
            return response

        elif filters.type == "inventario":
            reporte_inventario = get_reporte(final_area, final_categoria)
            return reporte_inventario
