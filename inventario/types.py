from .models import *
from graphene_django import DjangoObjectType
from graphene import ObjectType, Int, Field, List


class InfoType(ObjectType):
    total_pages = Int()
    page = Int()


class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude = ("password",)


class AreaVentaType(DjangoObjectType):
    class Meta:
        model = AreaVenta
        fields = "__all__"


class AreaVentaFilterType(ObjectType):
    areas_venta = List(AreaVentaType)
    info = Field(InfoType, required=False)
