from django.db import IntegrityError
from ninja.errors import HttpError
from inventario.models import AreaVenta, User
from inventario_v2.custom_permissions import isAdmin
from ..schema import UsuariosSchema, UsuariosAuthSchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404


@api_controller("usuarios/", tags=["Usuarios"], permissions=[isAdmin])
class UsuariosController:
    @route.get("", response=list[UsuariosSchema])
    def getUsuarios(self):
        return User.objects.all().exclude(is_superuser=True).order_by("-id")

    @route.post("")
    def addUsuario(self, data: UsuariosAuthSchema):
        dataDict = data.model_dump()

        try:
            user = User.objects.create(
                username=dataDict["username"], rol=dataDict["rol"]
            )

            if dataDict["rol"] == "ADMIN":
                user.is_staff = True

            if dataDict["area_venta"] is not None:
                area_venta = get_object_or_404(AreaVenta, pk=dataDict["area_venta"])
                user.area_venta = area_venta

            user.set_password(dataDict["password"])
            user.save()
            return "Usuario creado con éxito."
        except Exception as e:
            if isinstance(e, IntegrityError):
                raise HttpError(400, "El usuario ya existe.")
            else:
                raise HttpError(500, "Error inesperado.")

    @route.put("{id}/")
    def updateUsuario(self, id: int, data: UsuariosAuthSchema):
        dataDict = data.model_dump()
        print(dataDict)
        try:
            user = get_object_or_404(User, pk=id)
            user.username = dataDict["username"]
            user.rol = dataDict["rol"]
            if dataDict["password"]:
                user.set_password(dataDict["password"])
            if not dataDict["area_venta"]:
                user.area_venta = None
            else:
                area = get_object_or_404(AreaVenta, pk=dataDict["area_venta"])
                user.area_venta = area
            user.save()
            return {"success": True}

        except:
            raise HttpError(500, "Error inesperado")

    @route.delete("{id}/")
    def deleteUsuario(self, id: int):
        usuario = get_object_or_404(User, pk=id)
        try:
            usuario.delete()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")
