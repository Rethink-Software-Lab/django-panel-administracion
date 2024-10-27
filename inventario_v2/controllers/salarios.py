from ninja.errors import HttpError
from inventario.models import User, Salario

from ..schema import AllSalariosSchema, SalarioModifySchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin


@api_controller("salarios/", tags=["Salarios"], permissions=[isAdmin])
class SalariosController:
    @route.get("", response=AllSalariosSchema)
    def get_all_salarios(self):
        salarios = Salario.objects.all().select_related("usuario").order_by("-id")

        usuarios = User.objects.all()

        return {
            "salarios": salarios,
            "usuarios": usuarios,
        }

    @route.post("")
    def addSalario(self, body: SalarioModifySchema):
        body_dict = body.model_dump()

        usuario = get_object_or_404(User, pk=body_dict["usuario"])

        if Salario.objects.filter(usuario=usuario).exists():
            raise HttpError(400, "El usuario ya tiene un salario")

        cantidad = body_dict["cantidad"]

        try:
            Salario.objects.create(usuario=usuario, cantidad=cantidad)
            return
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")

    @route.delete("{id}/")
    def deleteSalario(self, id: int):
        salario = get_object_or_404(Salario, pk=id)

        try:
            salario.delete()
            return
        except:
            raise HttpError(500, "Error inesperado.")
