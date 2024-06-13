from .models import *
from graphene_django import DjangoObjectType
from graphene.types.generic import GenericScalar
from .cloudinary_scalar import CloudinaryScalar
from graphene.relay import Node
from graphene import ObjectType, Int, Field, List, ID, String, Decimal

class InfoType(ObjectType):
    total_pages = Int()
    page = Int()

class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude = ('password',)

class UserFilterType(ObjectType):
    users = List(UserType)
    info = Field(InfoType)

class ProductoType(DjangoObjectType):
    class Meta:
        model = Producto
        fields = '__all__'

class ProductFilterType(ObjectType):
    productos = List(ProductoType)
    info = Field(InfoType)

class ImagenType(ObjectType):
    url = CloudinaryScalar()

class ProductInfoType(DjangoObjectType):
    imagen = Field(ImagenType)
    class Meta:
        model = ProductoInfo
        fields = '__all__'


class ProductInfoFilterType(ObjectType):
    productos_info = List(ProductInfoType)
    info = Field(InfoType, required=False)

class EntradaAlmacenType(DjangoObjectType):
    class Meta:
        model = EntradaAlmacen
        fields = '__all__'
        
class EntradaFilterType(ObjectType):
    entradas = List(EntradaAlmacenType)
    info = Field(InfoType)

class SalidaAlmacenType(DjangoObjectType):
    class Meta:
        model = SalidaAlmacen
        fields = '__all__'

class SalidaFilterType(ObjectType):
    salidas = List(SalidaAlmacenType)
    info = Field(InfoType)

class PuntoVentaType(DjangoObjectType):
    class Meta:
        model = PuntoVenta
        fields = '__all__'

class PuntoVentaFilterType(ObjectType):
    puntos_venta = List(PuntoVentaType)
    info = Field(InfoType, required=False)

class NumerosType(ObjectType):
    numero = String()
    ids = String()

class AddEntradaType(ObjectType):
    color = String()
    numeros = List(NumerosType)

class VentasType(DjangoObjectType):
    class Meta:
        model = Ventas
        fields = '__all__'

class VentasFilterType(ObjectType):
    ventas = List(VentasType)
    info = Field(InfoType, required=False)

class PbyPT(ObjectType):
    id = ID()

class MasVendidosType(ObjectType):
    producto = Field(ProductInfoType)
    cantidad = Int()

class GraficoType(ObjectType):
    mes = String()
    ventas = String()