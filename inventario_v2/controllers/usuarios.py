from django.db import IntegrityError
from ninja.errors import HttpError
from inventario.models import AreaVenta, User, RolesChoices
from inventario_v2.custom_permissions import isAdmin
from ..schema import GetUsuariosSchema, UsuariosAuthSchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404


@api_controller("usuarios/", tags=["Usuarios"], permissions=[isAdmin])
class UsuariosController:
    @route.get("", response=GetUsuariosSchema)
    def getUsuarios(self):
        usuarios = User.objects.all().exclude(is_superuser=True).order_by("-id")
        areas_ventas = AreaVenta.objects.all()
        return {"usuarios": usuarios, "areas_ventas": areas_ventas}

    @route.post("")
    def addUsuario(self, data: UsuariosAuthSchema):
        dataDict = data.model_dump()

        try:
            user = User.objects.create(
                username=dataDict["username"], rol=dataDict["rol"]
            )

            if dataDict["rol"] == RolesChoices.ADMIN:
                user.is_staff = True

            if dataDict["rol"] == RolesChoices.VENDEDOR:
                area_venta = get_object_or_404(AreaVenta, pk=dataDict["area_venta"])
                user.area_venta = area_venta

            if dataDict["rol"] == RolesChoices.ALMACENERO:
                user.almacen = dataDict["almacen"]

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
        try:
            user = get_object_or_404(User, pk=id)
            user.username = dataDict["username"]
            user.rol = dataDict["rol"]
            if dataDict["password"]:
                user.set_password(dataDict["password"])
            if dataDict["rol"] == RolesChoices.VENDEDOR:
                area = get_object_or_404(AreaVenta, pk=dataDict["area_venta"])
                user.area_venta = area
                user.almacen = None

            if dataDict["rol"] == RolesChoices.ALMACENERO:
                user.almacen = dataDict["almacen"]
                user.area_venta = None

            if dataDict["rol"] == RolesChoices.ADMIN:
                user.is_staff = True
                user.area_venta = None
                user.almacen = None

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
