from typing import List
from graphene import List, ObjectType, Field, ID
from .types import *
from .models import *
from graphql_jwt.decorators import login_required, staff_member_required, user_passes_test
from datetime import timedelta, datetime, date
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
    productos_by_punto_venta = List(PbyPT, id=ID())
    one_producto=Field(ProductoType, id=ID())
    all_punto_venta = Field(PuntoVentaFilterType, page=Int(required=False))
    inventario_almacen = Field(ProductFilterType, page=Int())
    inventario_punto_venta = Field(ProductFilterType, id=ID(), id_producto=ID(), codigo=String(), page=Int())
    search_product = Field(ProductInfoType, codigo=String())
    mas_vendidos = List(MasVendidosType)
    ventas_hoy = Decimal()
    ventas_semana = Decimal()
    ventas_mes = Decimal()
    grafico = List(GraficoType)
    one_ventas = Field(VentasFilterType, id=ID(), page=Int())
    one_user = Field(UserType, id=ID(required=True))
    user_by_token = Field(UserType)

    @staff_member_required
    def resolve_all_users(self, info, page=1, perPage=7):
        p = Paginator(User.objects.all().order_by('-id').exclude(id=1), per_page=perPage)
        users = p.get_page(page)
        return UserFilterType(users, info=InfoType(page=page, total_pages=p.num_pages))
    
    @staff_member_required
    def resolve_one_user(self, info, id):
        user = get_object_or_404(User, pk=id)
        return user
    
    @login_required
    def resolve_all_productos_info(self, info, page=None):
        if page is None:
            productos_info = ProductoInfo.objects.all().order_by('-id')  
            return ProductInfoFilterType(productos_info)
        p = Paginator(ProductoInfo.objects.all().order_by('-id'), 7)
        productos_info = p.get_page(page)
        return ProductInfoFilterType(productos_info, info=InfoType(page=page, total_pages=p.num_pages))
    
    @login_required
    def resolve_one_product_info(self, info, id):
        return get_object_or_404(ProductoInfo, pk=id)
    
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_all_entradas(self, info, page=1):
        p = Paginator(EntradaAlmacen.objects.all().order_by('-created_at'), 7)
        entradas = p.get_page(page)
        return EntradaFilterType(entradas, info=InfoType(page=page, total_pages=p.num_pages))
    
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_all_salidas(self, info, page=1):
        p = Paginator(SalidaAlmacen.objects.all().order_by('-created_at'), 7)
        salidas = p.get_page(page)
        return SalidaFilterType(salidas, info=InfoType(page=page, total_pages=p.num_pages))
    
    @login_required
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def resolve_all_punto_venta(self, info, page=None):
        if page is None:
            puntos_venta = PuntoVenta.objects.all().order_by('-id')  
            return PuntoVentaFilterType(puntos_venta)
        p = Paginator(PuntoVenta.objects.all().order_by('-id'), 7)
        puntos_venta = p.get_page(page)
        return PuntoVentaFilterType(puntos_venta, info=InfoType(page=page, total_pages=p.num_pages))
    
    @login_required
    def resolve_inventario_almacen(self, info, page=None):
        if page is None:
            productos = Producto.objects.filter(punto_venta=None, in_stock=True).order_by('-id')
            return ProductFilterType(productos)
        p = Paginator(Producto.objects.filter(punto_venta=None, in_stock=True).order_by('-id'), 7)
        productos = p.get_page(page)
        return ProductFilterType(productos, info=InfoType(page=page, total_pages=p.num_pages))
    
    @login_required
    def resolve_inventario_punto_venta(self, info, id, id_producto=None, codigo=None, page=None):
        filtros = {}
        if id_producto is not None:
            filtros['id'] = id_producto
        if codigo is not None:
            filtros['info__codigo'] = codigo
        p = Paginator(Producto.objects.filter(**filtros, punto_venta__id=id, in_stock=True).order_by('-id'), 7)
        productos = p.get_page(page)
        return ProductFilterType(productos, info=InfoType(page=page, total_pages=p.num_pages))
    
    @login_required
    def resolve_one_ventas(self, info, id, page=None):
        if info.context.user.rol == "ADMIN" or info.context.user.rol == "ALMACENERO" or info.context.user.punto_venta.id == int(id):
            if page is None:
                ventas = Ventas.objects.filter(punto_venta__id=id).order_by('-id')  
                return PuntoVentaFilterType(ventas)
            p = Paginator(Ventas.objects.filter(punto_venta__id=id).order_by('-id'), 7)
            ventas = p.get_page(page)
            return VentasFilterType(ventas, info=InfoType(page=page, total_pages=p.num_pages))
        else:
            return GraphQLError("No tienes permisos para relizar esta acción")
    
    @login_required
    def resolve_search_product(self, info, codigo):
        producto = get_object_or_404(ProductoInfo, codigo__icontains=codigo)
        return producto
        
    @login_required
    def resolve_productos_by_punto_venta(self, info, id):
        if info.context.user.rol == "ADMIN" or info.context.user.punto_venta.id == int(id):
            productos = Producto.objects.filter(punto_venta__id=id, in_stock=True).values('id')
            return productos
        else:
            return GraphQLError("No tienes permisos para relizar esta acción")
        
    @login_required
    def resolve_one_producto(self, info, id):
        return get_object_or_404(Producto, pk=id)

        
    @staff_member_required
    def resolve_mas_vendidos(self, info):
        product_info = ProductoInfo.objects.all()
        products = []

        for prod_info in product_info:
            productos = Producto.objects.filter(in_stock=False, info=prod_info).count()
            if productos < 1:
                continue
            products.append({
                "producto": prod_info,
                "cantidad": productos 
            })

        products.sort(key=lambda producto: producto['cantidad'], reverse=True)
        return products[0:5]
    
    @staff_member_required
    def resolve_ventas_hoy(self, info):
        ventas = Ventas.objects.filter(created_at__date=date.today())
       
        m = 0

        for venta in ventas:
            productos = venta.productos.all()
            products = Producto.objects.filter(pk__in=productos)
            for product in products:
                m += product.info.precio_venta - product.info.precio_costo
        return m
    
    @staff_member_required
    def resolve_ventas_semana(self, info):

        hoy = timezone.now().date()

        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        ventas = Ventas.objects.filter(created_at__date__range=(inicio_semana, fin_semana))
        
        m = 0

        for venta in ventas:
            productos = venta.productos.all()
            products = Producto.objects.filter(pk__in=productos)
            for product in products:
                m += product.info.precio_venta - product.info.precio_costo
        return m
    
    @staff_member_required
    def resolve_ventas_mes(self, info):

        mes_actual = datetime.now().month

        ventas = Ventas.objects.filter(created_at__date__month=mes_actual)
        
        m = 0

        for venta in ventas:
            productos = venta.productos.all()
            products = Producto.objects.filter(pk__in=productos)
            for product in products:
                m += product.info.precio_venta - product.info.precio_costo
        return m
    
    @staff_member_required
    def resolve_grafico(self, info):
        anno = datetime.now().year

        mes_actual = datetime.now().month

        if mes_actual > 0:
            grafico = [] 
            for mes in range(1, mes_actual+1):
                ventas = Ventas.objects.filter(created_at__date__year=anno, created_at__date__month=mes)
                v = 0
                nombre_mes = ""
                if ventas.count() > 0:
                    for venta in ventas:
                        productos = venta.productos.all()
                        products = Producto.objects.filter(pk__in=productos)
                        nombre_mes = get_month_name(mes)
                        for product in products:
                            v += product.info.precio_venta - product.info.precio_costo
                else:
                    nombre_mes = get_month_name(mes)
                grafico.append({
                    "mes": nombre_mes.capitalize(),
                    "ventas": v
                })
            return grafico

    
    @login_required
    def resolve_user_by_token(self, info):
        try:
            token = info.context.headers['Authorization']
            tk = token[4:len(token)]
            return get_user_by_token(tk)
        except User.DoesNotExist:
            return GraphQLError('El token es incorrecto o no existe')