import datetime
from ninja import ModelSchema, Schema
from inventario.models import *
from typing import List, Optional, Literal, Any
from pydantic import condecimal, conint, validator
from decimal import Decimal


class TokenSchema(Schema):
    token: str


class LoginSchema(Schema):
    username: str
    password: str


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


class ProductoWithCategotiaSchema(Schema):
    productos: List[ProductoInfoSchema]
    categorias: List[CategoriasSchema]


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
    producto__info__descripcion: str | None
    created_at: datetime.datetime
    cantidad: int


class AddEntradaSchema(Schema):
    metodoPago: str
    proveedor: str
    variantes: Optional[List[VariantesSchema]] = None
    cantidad: Optional[int] = None
    productInfo: str
    comprador: str


class AreaVentaSchema(ModelSchema):
    class Meta:
        model = AreaVenta
        fields = "__all__"


class AreaVentaModifySchema(ModelSchema):
    class Meta:
        model = AreaVenta
        exclude = ("id",)


class Salidas(Schema):
    id: int
    area_venta__nombre: str | None
    usuario__username: str
    producto__info__descripcion: str | None
    created_at: datetime.datetime
    cantidad: int

    @validator("area_venta__nombre", pre=True, always=True)
    def set_default_area_venta(cls, v):
        return v or "Almacén Revoltosa"


class ProductoCodigoSchema(Schema):
    codigo: str
    categoria: CategoriasSchema


class SalidaAlmacenSchema(Schema):
    salidas: List[Salidas]
    areas_de_venta: List[AreaVentaSchema]
    productos: List[ProductoCodigoSchema]


class SalidaAlmacenRevoltosaSchema(Schema):
    id: int
    usuario__username: str
    producto__info__descripcion: str | None
    created_at: datetime.datetime
    cantidad: int


class ProductoInfoSalidaAlmacenRevoltosaSchema(Schema):
    salidas: List[SalidaAlmacenRevoltosaSchema]
    productos: List[ProductoCodigoSchema]


class AddSalidaSchema(Schema):
    area_venta: int | Literal["almacen-revoltosa"]
    producto_info: str
    cantidad: Optional[int] = None
    zapatos_id: Optional[List[int]] = None


class AddSalidaRevoltosaSchema(Schema):
    producto_info: str
    cantidad: Optional[int] = None
    zapatos_id: Optional[List[int]] = None


class VentasSchema(Schema):
    id: int
    created_at: datetime.datetime
    importe: condecimal() | None
    metodo_pago: str
    usuario__username: str
    producto__info__descripcion: str | None
    cantidad: int


class AddVentaSchema(Schema):
    areaVenta: int
    metodoPago: Literal["EFECTIVO", "TRANSFERENCIA", "MIXTO"]
    producto_info: str
    cantidad: Optional[int] = None
    zapatos_id: Optional[List[int]] = None
    efectivo: Optional[condecimal(gt=0)] = None
    transferencia: Optional[condecimal(gt=0)] = None

    @validator("efectivo", "transferencia", pre=True, always=True)
    def check_mixto(cls, v, values, **kwargs):
        if values.get("metodoPago") == "MIXTO":
            if v is None:
                raise ValueError(
                    "efectivo y transferencia deben tener valor si metodoPago es MIXTO"
                )
        else:
            if v is not None:
                raise ValueError(
                    "efectivo y transferencia deben ser None si metodoPago no es MIXTO"
                )
        return v


class OtrosProductos(Schema):
    id: int
    codigo: str
    descripcion: str
    precio_venta: condecimal(gt=0)
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
    total: condecimal() | None
    pago_trabajador: conint(ge=0) | None
    costo_producto: condecimal() | None
    subtotal: condecimal(ge=0) | None
    efectivo: condecimal(ge=0) | None
    transferencia: condecimal(ge=0) | None
    area: Optional[str] = None


class Zapatos(Schema):
    id: int
    info__codigo: str
    info__descripcion: str
    color: str
    numero: int


class InventarioSchema(Schema):
    productos: List[OtrosProductos]
    zapatos: List[Zapatos]


class InventarioAreaVentaSchema(Schema):
    productos: List[OtrosProductos]
    zapatos: List[Zapatos]
    categorias: List[CategoriasSchema]


class OneAreaVentaSchema(Schema):
    inventario: InventarioAreaVentaSchema
    ventas: List[VentasSchema]
    area_venta: str
    all_productos: List[ProductoInfoSchema]


class Almacenes(Schema):
    inventario: InventarioSchema
    categorias: List[CategoriasSchema]


class AddProductoSchema(Schema):
    codigo: str
    descripcion: str
    categoria: int
    precio_costo: condecimal(gt=0)
    precio_venta: condecimal(gt=0)
    pago_trabajador: conint(ge=0)


class UpdateProductoSchema(Schema):
    codigo: str
    descripcion: str
    categoria: int
    precio_costo: condecimal(gt=0)
    precio_venta: condecimal(gt=0)
    pago_trabajador: conint(ge=0)
    deletePhoto: bool


class UsuariosSchema(ModelSchema):
    area_venta: Optional[AreaVentaSchema] = None

    class Meta:
        model = User
        fields = ["id", "username", "rol"]


class GetUsuariosSchema(Schema):
    usuarios: List[UsuariosSchema]
    areas_ventas: List[AreaVentaSchema]


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


# class VentasPorAreaSchema(Schema):
#     dia: str
#     str Dict[str, Dict[str, Any]]


class VentasAnualesSchema(Schema):
    mes: str
    ventas: Decimal


class MasVendidosSchema(Schema):
    producto: ProductoInfoSchema
    cantidad: int


class GraficasSchema(Schema):
    ventasPorArea: Any
    ventasAnuales: List[VentasAnualesSchema]
    masVendidos: List[MasVendidosSchema]
    ventasHoy: Decimal
    ventasSemana: Decimal
    ventasMes: Decimal


class ProductosDentroDeTransferencia(Schema):
    descripcion: str
    total_transfers: int


class TransferenciaSchema(ModelSchema):
    usuario: UsuariosSchema
    de: AreaVentaSchema
    para: AreaVentaSchema
    productos: List[ProductosDentroDeTransferencia]

    class Meta:
        model = Transferencia
        fields = "__all__"


class AllTransferenciasSchema(Schema):
    transferencias: List[TransferenciaSchema]
    areas_ventas: List[AreaVentaSchema]
    productos_info: List[ProductoInfoSchema]


class ProductosTransfer(Schema):
    producto: int
    cantidad: Optional[int] = None
    zapatos_id: Optional[str] = None


class TransferenciasModifySchema(Schema):
    de: int
    para: int
    productos: List[ProductosTransfer]


class AjusteSchema(ModelSchema):
    usuario: UsuariosSchema
    productos: List[ProductosDentroDeTransferencia]

    class Meta:
        model = AjusteInventario
        fields = "__all__"


class AllAjustesSchema(Schema):
    ajustes: List[AjusteSchema]
    areas_ventas: List[AreaVentaSchema]
    productos_info: List[ProductoInfoSchema]


class ProductosAjuste(Schema):
    producto: int
    cantidad: Optional[int] = None
    zapatos_id: Optional[str] = None
    area_venta: Optional[str] = None


class AjustesModifySchema(Schema):
    motivo: str
    productos: List[ProductosAjuste]
