from ninja_extra.permissions import BasePermission, SAFE_METHODS


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class isAdmin(BasePermission):
    def has_permission(self, request, view=None, controller=None):
        return request.auth["rol"] == "ADMIN"


class isStaff(BasePermission):
    def has_permission(self, request, view=None, controller=None):
        return request.auth["rol"] == "ADMIN" or request.auth == "ALMACENERO"
