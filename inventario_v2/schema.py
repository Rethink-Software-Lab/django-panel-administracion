from ninja import ModelSchema, Schema
from inventario.models import *
from typing import List, Optional


class UsuariosSchema(ModelSchema):
    class Meta:
        model = User
        fields = ["id", "username", "rol"]


class UserModifySchema(Schema):
    username: str
    rol: str = "OFICINISTA"
    password: str


class CategoriasSchema(ModelSchema):
    class Meta:
        model = Categorias
        fields = "__all__"


class CategoriasModifySchema(ModelSchema):
    class Meta:
        model = Categorias
        exclude = ["id"]


class NumerosSchema(Schema):
    numero: float
    cantidad: int


class VariantesSchema(Schema):
    color: str
    numeros: List[NumerosSchema]


class AddEntradaSchema(Schema):
    metodoPago: str
    proveedor: str
    variantes: Optional[List[VariantesSchema]] = None
    cantidad: Optional[int] = None
    productInfo: str
    comprador: str
    
class AddSalidaSchema(Schema):
    areaVenta: int
    producto_info: str
    cantidad: Optional[int] = None
    zapatos_id: Optional[List[int]] = None
    
class AddVentaSchema(Schema):
    areaVenta: int
    metodoPago: str
    producto_info: str
    cantidad: Optional[int] = None
    zapatos_id: Optional[List[int]] = None
    
class OtrosProductos(Schema):
    id: int
    codigo: str
    descripcion: str
    cantidad: int
    categoria__nombre: str

class ProductoInfoSchema(ModelSchema):
    categoria: CategoriasSchema

    class Meta:
        model = ProductoInfo
        fields = "__all__"


class Zapatos(ModelSchema):
    info: ProductoInfoSchema

    class Meta:
        model = Producto
        fields = "__all__"
        
class InventarioSchema(Schema):
    productos: List[OtrosProductos]
    zapatos: List[Zapatos]
