from typing import List
from graphene import List, ObjectType, Field, ID
from .types import *
from .models import *
from graphql_jwt.decorators import (
    login_required,
    staff_member_required,
    user_passes_test,
)

from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from graphql import GraphQLError


class Query(ObjectType):
    all_users = Field(UserFilterType, page=Int(), perPage=Int())
    one_user = Field(UserType, id=ID())
    all_productos_info = Field(ProductInfoFilterType, page=Int(), perPage=Int())
    one_product_info = Field(ProductInfoType, id=ID())
    all_salidas = Field(SalidaFilterType, page=Int())
    productos_by_area_venta = List(PbyPT, id=ID())
    one_producto = Field(ProductoType, id=ID())
    all_area_venta = Field(AreaVentaFilterType, page=Int(required=False))
    inventario_almacen = List(ProductoType)
    inventario_area_venta = List(ProductoType, id=ID())
    mas_vendidos = List(MasVendidosType)
    one_ventas = Field(VentasFilterType, id=ID(), page=Int())

    @staff_member_required
    def resolve_all_users(self, info, page=1, perPage=7):
        p = Paginator(
            User.objects.all().order_by("-id").exclude(id=1), per_page=perPage
        )
        users = p.get_page(page)
        return UserFilterType(users, info=InfoType(page=page, total_pages=p.num_pages))

    @staff_member_required
    def resolve_one_user(self, info, id):
        user = get_object_or_404(User, pk=id)
        return user

    @login_required
    def resolve_all_productos_info(self, info, page=None):
        if page is None:
            productos_info = ProductoInfo.objects.all().order_by("-id")
            return ProductInfoFilterType(productos_info)
        p = Paginator(ProductoInfo.objects.all().order_by("-id"), 20)
        productos_info = p.get_page(page)
        return ProductInfoFilterType(
            productos_info, info=InfoType(page=page, total_pages=p.num_pages)
        )

    @login_required
    def resolve_one_product_info(self, info, id):
        return get_object_or_404(ProductoInfo, pk=id)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_all_salidas(self, info, page=1):
        p = Paginator(SalidaAlmacen.objects.all().order_by("-created_at"), 20)
        salidas = p.get_page(page)
        return SalidaFilterType(
            salidas, info=InfoType(page=page, total_pages=p.num_pages)
        )

    @login_required
    def resolve_all_area_venta(self, info, page=None):
        if page is None:
            areas_venta = AreaVenta.objects.all().order_by("-id")
            return AreaVentaFilterType(areas_venta)
        p = Paginator(AreaVenta.objects.all().order_by("-id"), 20)
        areas_venta = p.get_page(page)
        return AreaVentaFilterType(
            areas_venta, info=InfoType(page=page, total_pages=p.num_pages)
        )

    @login_required
    def resolve_inventario_almacen(self, info):
        productos = Producto.objects.filter(
            area_venta=None, venta__isnull=True
        ).order_by("-id")
        return productos

    @login_required
    def resolve_inventario_area_venta(self, info, id):
        productos = Producto.objects.filter(
            area_venta__id=id, venta__isnull=True
        ).order_by("-id")
        return productos

    @login_required
    def resolve_one_ventas(self, info, id, page=None):
        if (
            info.context.user.rol == "ADMIN"
            or info.context.user.rol == "ALMACENERO"
            or info.context.user.area_venta.id == int(id)
        ):
            if page is None:
                ventas = Ventas.objects.filter(area_venta__id=id).order_by("-id")
                return AreaVentaFilterType(ventas)
            p = Paginator(Ventas.objects.filter(area_venta__id=id).order_by("-id"), 20)
            ventas = p.get_page(page)
            print(ventas)
            return VentasFilterType(
                ventas, info=InfoType(page=page, total_pages=p.num_pages)
            )
        else:
            return GraphQLError("No tienes permisos para relizar esta acción")

    @login_required
    def resolve_productos_by_area_venta(self, info, id):
        if info.context.user.rol == "ADMIN" or info.context.user.area_venta.id == int(
            id
        ):
            productos = Producto.objects.filter(
                area_venta__id=id, venta__isnull=True
            ).values("id")
            return productos
        else:
            return GraphQLError("No tienes permisos para relizar esta acción")

    @login_required
    def resolve_one_producto(self, info, id):
        return get_object_or_404(Producto, pk=id)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_mas_vendidos(self, info):

        product_info = ProductoInfo.objects.all()
        products = []

        if product_info:
            for prod_info in product_info:
                productos = Producto.objects.filter(
                    venta__isnull=False, info=prod_info
                ).count()
                if productos < 1:
                    continue
                products.append({"producto": prod_info, "cantidad": productos})

            products.sort(key=lambda producto: producto["cantidad"], reverse=True)
        return products[0:5]
