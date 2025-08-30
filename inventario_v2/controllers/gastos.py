from ninja.errors import HttpError
from inventario.models import User, Gastos, GastosChoices, AreaVenta

from ..schema import  GastosModifySchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin


@api_controller("gastos/", tags=["Gastos"], permissions=[isAdmin])
class GastosController:
    
    @route.post("")
    def add_gastos(self, request, body: GastosModifySchema):
        body_dict = body.model_dump()

        usuario = get_object_or_404(User, pk=request.auth["id"])
        if body_dict["area_venta"] != "cafeteria":
            area_venta = get_object_or_404(AreaVenta, pk=body_dict["area_venta"])
        tipo = body_dict["tipo"]
        dia_mes = body_dict["dia_mes"]
        frecuencia = body_dict["frecuencia"]
        cantidad = body_dict["cantidad"]
        descripcion = body_dict["descripcion"]
        dia_semana = body_dict["dia_semana"]

        try:
            if body_dict["area_venta"] == "cafeteria":
                Gastos.objects.create(
                    usuario=usuario,
                    is_cafeteria=True,
                    tipo=tipo,
                    cantidad=cantidad,
                    descripcion=descripcion,
                    dia_mes=dia_mes,
                    frecuencia=frecuencia,
                    dia_semana=dia_semana,
                )
            else:
                Gastos.objects.create(
                    usuario=usuario,
                    area_venta=area_venta,
                    tipo=tipo,
                    cantidad=cantidad,
                    descripcion=descripcion,
                    dia_mes=dia_mes,
                    frecuencia=frecuencia,
                    dia_semana=dia_semana,
                )
            return
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")

    @route.put("{id}/")
    def edit_gasto(self, id: int, body: GastosModifySchema):
        gasto = get_object_or_404(Gastos, pk=id)
        body_dict = body.model_dump()

        if body_dict["area_venta"] != "cafeteria":
            area_venta = get_object_or_404(AreaVenta, pk=body_dict["area_venta"])

        gasto.tipo = body_dict["tipo"]
        gasto.descripcion = body_dict["descripcion"]
        gasto.area_venta = (
            area_venta if body_dict["area_venta"] != "cafeteria" else None
        )
        gasto.is_cafeteria = True if body_dict["area_venta"] == "cafeteria" else False
        gasto.cantidad = body_dict["cantidad"]
        gasto.frecuencia = body_dict["frecuencia"]
        gasto.dia_mes = body_dict["dia_mes"]
        gasto.dia_semana = body_dict["dia_semana"]

        try:
            gasto.save()
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")

    @route.delete("{id}/")
    def delete_gasto(self, id: int):
        gasto = get_object_or_404(Gastos, pk=id)

        try:
            gasto.delete()
            return
        except:
            raise HttpError(500, "Error inesperado.")
