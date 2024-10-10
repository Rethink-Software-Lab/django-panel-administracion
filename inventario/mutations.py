from graphene import String, ID, Mutation, Field, ObjectType
from graphql import GraphQLError
from django.shortcuts import get_object_or_404


from graphql_jwt.decorators import user_passes_test

import graphql_jwt
from .types import *
from .models import *


class AddAreaVenta(Mutation):
    class Arguments:
        nombre = String(required=True)
        color = String(required=True)

    area_venta = Field(AreaVentaType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, nombre, color):
        area_venta = AreaVenta.objects.create(nombre=nombre, color=color)
        area_venta.save()
        return AddAreaVenta(area_venta)


class UpdateAreaVenta(Mutation):
    class Arguments:
        id = ID(required=True)
        nombre = String(required=True)
        color = String(required=True)

    area_venta = Field(AreaVentaType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id, nombre, color):

        area_venta = get_object_or_404(AreaVenta, pk=id)
        area_venta.nombre = nombre
        area_venta.color = color
        area_venta.save()

        return UpdateAreaVenta(area_venta)


class DeleteAreaVenta(Mutation):
    class Arguments:
        id = ID(required=True)

    message = String()

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id):
        try:
            area_venta = get_object_or_404(AreaVenta, pk=id)
            area_venta.delete()
            return DeleteAreaVenta(message="Área de venta eliminada con éxito")
        except EntradaAlmacen.DoesNotExist:
            return GraphQLError("Área de venta no encontrada")
        except:
            return GraphQLError("Something went wrong XC")


class ObtainJSONWebToken(graphql_jwt.JSONWebTokenMutation):
    user = Field(UserType)

    @classmethod
    def resolve(cls, root, info, **kwargs):
        return cls(user=info.context.user)


class Mutations(ObjectType):
    add_area_venta = AddAreaVenta.Field()
    update_area_venta = UpdateAreaVenta.Field()
    delete_area_venta = DeleteAreaVenta.Field()
    login = ObtainJSONWebToken.Field()
