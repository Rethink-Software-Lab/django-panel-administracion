from ninja_extra.permissions import BasePermission, SAFE_METHODS
from inventario.models import User


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class isAdmin(BasePermission):
    def has_permission(self, request, view=None, controller=None):
        return request.auth["rol"] == "ADMIN"


class isStaff(BasePermission):
    def has_permission(self, request, view=None, controller=None):
        return request.auth["rol"] == "ADMIN" or request.auth["rol"] == "ALMACENERO"


class isAuthenticated(BasePermission):
    def has_permission(self, request, view=None, controller=None):
        if request.auth:
            return True


# TODO
# class isAuthorizeVenta(BasePermission):
#     def has_permission(self, request, view=None, controller=None):
#         import re
#         import json

#         if request.method != "POST":
#             match = re.search(r"/v2/ventas/(\d+)/", request.path)
#             if match:
#                 try:
#                     id_venta = int(match.group(1))
#                     return request.user.area_venta == id_venta
#                 except ValueError:
#                     return False

#         data = json.loads(request.body)
#         return data.get("area_venta") == request.user.area_venta
