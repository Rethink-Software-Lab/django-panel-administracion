import datetime
from ninja import ModelSchema, Schema
from inventario.models import *
from typing import List, Optional
from pydantic import condecimal, HttpUrl


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


class ImagenSchema(ModelSchema):
    class Meta:
        model = Image
        fields = "__all__"


class ProductoInfoSchema(ModelSchema):
    imagen: Optional[ImagenSchema] = None
    categoria: CategoriasSchema

    class Meta:
        model = ProductoInfo
        fields = "__all__"


class ProductoSchema(ModelSchema):
    info: ProductoInfoSchema

    class Meta:
        model = Producto
        fields = "__all__"


class EntradaAlmacenSchema(Schema):
    id: int
    metodo_pago: str
    proveedor: str
    comprador: str
    usuario__username: str
    producto__info__descripcion: str
    created_at: datetime.datetime
    cantidad: int


class AddEntradaSchema(Schema):
    metodoPago: str
    proveedor: str
    variantes: Optional[List[VariantesSchema]] = None
    cantidad: Optional[int] = None
    productInfo: str
    comprador: str


class SalidaAlmacenSchema(Schema):
    id: int
    area_venta__nombre: str
    usuario__username: str
    producto__info__descripcion: str
    created_at: datetime.datetime
    cantidad: int


class AddSalidaSchema(Schema):
    area_venta: int
    producto_info: str
    cantidad: Optional[int] = None
    zapatos_id: Optional[List[int]] = None


class VentasSchema(Schema):
    id: int
    created_at: datetime.datetime
    importe: condecimal(gt=0)
    metodo_pago: str
    usuario__username: str
    producto__info__descripcion: str
    cantidad: int


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


class ProductoInfoModifySchema(Schema):
    id: int
    descripcion: str
    cantidad: int
    precio_venta: condecimal(gt=0)
    importe: condecimal(gt=0)


class VentaReporteSchema(Schema):
    productos: List[ProductoInfoModifySchema]
    total: condecimal(gt=0) | None
    area: str | None


class Zapatos(ModelSchema):
    info: ProductoInfoSchema

    class Meta:
        model = Producto
        fields = "__all__"


class InventarioSchema(Schema):
    productos: List[OtrosProductos]
    zapatos: List[Zapatos]


class AddProductoSchema(Schema):
    codigo: str
    descripcion: str
    categoria: int
    precio_costo: condecimal(gt=0)
    precio_venta: condecimal(gt=0)


class UpdateProductoSchema(Schema):
    codigo: str
    descripcion: str
    categoria: int
    imagen: Optional[HttpUrl] = None
    precio_costo: condecimal(gt=0)
    precio_venta: condecimal(gt=0)


class AreaVentaSchema(ModelSchema):
    class Meta:
        model = AreaVenta
        fields = "__all__"


class UsuariosSchema(ModelSchema):
    area_venta: Optional[AreaVentaSchema] = None

    class Meta:
        model = User
        fields = ["id", "username", "rol"]


class UsuariosAuthSchema(ModelSchema):
    area_venta: Optional[int] = None

    class Meta:
        model = User
        fields = ["username", "password", "rol"]


class Otros(Schema):
    area: str
    cantidad: int


class newZapatos(Schema):
    id: int
    color: str
    numero: int


class ZapatosForSearch(Schema):
    area: str
    productos: List[newZapatos]


class SearchProductSchema(Schema):
    info: ProductoInfoSchema
    zapato: bool
    inventario: List[Otros] | List[ZapatosForSearch]
