from typing import List
from graphene import List, ObjectType, Field, ID, Decimal
from .types import *
from .models import *
from graphql_jwt.decorators import (
    login_required,
    staff_member_required,
    user_passes_test,
)
from django.db.models import F, Sum
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from graphql_jwt.shortcuts import get_user_by_token
from django.core.paginator import Paginator
from graphql import GraphQLError
from .utils import get_month_name


class Query(ObjectType):
    all_users = Field(UserFilterType, page=Int(), perPage=Int())
    one_user = Field(UserType, id=ID())
    all_productos_info = Field(ProductInfoFilterType, page=Int(), perPage=Int())
    one_product_info = Field(ProductInfoType, id=ID())
    all_entradas = Field(EntradaFilterType, page=Int())
    all_salidas = Field(SalidaFilterType, page=Int())
    productos_by_area_venta = List(PbyPT, id=ID())
    one_producto = Field(ProductoType, id=ID())
    all_area_venta = Field(AreaVentaFilterType, page=Int(required=False))
    inventario_almacen = List(ProductoType)
    inventario_area_venta = List(ProductoType, id=ID())
    mas_vendidos = List(MasVendidosType)
    ventas_hoy = Decimal()
    ventas_semana = Decimal()
    ventas_mes = Decimal()
    grafico = List(GraficoType)
    one_ventas = Field(VentasFilterType, id=ID(), page=Int())
    user_by_token = Field(UserType)

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
    def resolve_all_entradas(self, info, page=1):
        p = Paginator(EntradaAlmacen.objects.all().order_by("-created_at"), 20)
        entradas = p.get_page(page)
        return EntradaFilterType(
            entradas, info=InfoType(page=page, total_pages=p.num_pages)
        )

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_all_salidas(self, info, page=1):
        p = Paginator(SalidaAlmacen.objects.all().order_by("-created_at"), 20)
        salidas = p.get_page(page)
        return SalidaFilterType(
            salidas, info=InfoType(page=page, total_pages=p.num_pages)
        )

    @login_required
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
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

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_ventas_hoy(self, info):
        productos = (
            Producto.objects.filter(venta__created_at__date=timezone.now().date())
            .annotate(diferencia=F("info__precio_venta") - F("info__precio_costo"))
            .aggregate(ventaHoy=Sum("diferencia"))
        )

        return productos["ventaHoy"]

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_ventas_semana(self, info):

        hoy = timezone.now().date()

        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)

        productos = (
            Producto.objects.filter(
                venta__created_at__range=[inicio_semana, fin_semana]
            )
            .annotate(diferencia=F("info__precio_venta") - F("info__precio_costo"))
            .aggregate(ventaSemana=Sum("diferencia"))
        )

        return productos["ventaSemana"]

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_ventas_mes(self, info):

        today = timezone.now().date()

        inicio_mes = today.replace(day=1)
        proximo_mes = inicio_mes.replace(day=28) + timedelta(
            days=4
        )  # Esto asegura estar en el próximo mes
        fin_mes = proximo_mes - timedelta(days=proximo_mes.day)

        productos = (
            Producto.objects.filter(venta__created_at__range=[inicio_mes, fin_mes])
            .annotate(diferencia=F("info__precio_venta") - F("info__precio_costo"))
            .aggregate(ventaMes=Sum("diferencia"))
        )

        return productos["ventaMes"]

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_grafico(self, info):
        anno = timezone.now().year

        mes_actual = timezone.now().month

        grafico = []
        if mes_actual > 0:
            for mes in range(1, mes_actual + 1):
                prod = (
                    Producto.objects.filter(
                        venta__created_at__date__year=anno,
                        venta__created_at__date__month=mes,
                    )
                    .annotate(
                        diferencia=F("info__precio_venta") - F("info__precio_costo")
                    )
                    .aggregate(total=Sum("diferencia"))
                )
                nombre_mes = get_month_name(mes)
                grafico.append(
                    {
                        "mes": nombre_mes.capitalize(),
                        "ventas": prod["total"] if prod["total"] else 0,
                    }
                )
        return grafico

    @login_required
    def resolve_user_by_token(self, info):
        try:
            token = info.context.headers["Authorization"]
            tk = token[4 : len(token)]
            return get_user_by_token(tk)
        except User.DoesNotExist:
            return GraphQLError("El token es incorrecto o no existe")
