from ninja.errors import HttpError
from inventario.models import User, Gastos, GastosChoices

from ..schema import AllGastosSchema, GastosModifySchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin


@api_controller("gastos/", tags=["Gastos"], permissions=[isAdmin])
class GastosController:
    @route.get("", response=AllGastosSchema)
    def get_all_gastos(self):
        gastos_fijos = (
            Gastos.objects.filter(tipo=GastosChoices.FIJO)
            .select_related("usuario")
            .order_by("-id")
        )
        gastos_variables = (
            Gastos.objects.filter(tipo=GastosChoices.VARIABLE)
            .select_related("usuario")
            .order_by("-id")
        )

        return {
            "fijos": gastos_fijos,
            "variables": gastos_variables,
        }

    @route.post("")
    def add_gastos(self, request, body: GastosModifySchema):
        body_dict = body.model_dump()

        usuario = get_object_or_404(User, pk=request.auth["id"])

        try:
            Gastos.objects.create(usuario=usuario, **body_dict)
            return
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")

    @route.put("{id}/")
    def edit_gasto(self, id: int, body: GastosModifySchema):
        gasto = get_object_or_404(Gastos, pk=id)
        body_dict = body.model_dump()

        gasto.tipo = body_dict["tipo"]
        gasto.descripcion = body_dict["descripcion"]
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
