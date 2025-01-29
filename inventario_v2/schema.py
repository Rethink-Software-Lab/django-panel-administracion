import datetime
from ninja import ModelSchema, Schema
from inventario.models import *
from typing import List, Optional, Literal, Any
from pydantic import condecimal, conint, validator, Field
from decimal import Decimal
from typing_extensions import Annotated


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
    usuario__username: Optional[str] = None
    producto__info__descripcion: Optional[str] = None
    created_at: datetime.datetime
    cantidad: int


class ProductoParaEntradaAlmacenCafeteriaSchema(Schema):
    id: int
    codigo: str
    descripcion: str


class AreaVentaSchema(ModelSchema):
    class Meta:
        model = AreaVenta
        fields = "__all__"


class UsuariosSchema(ModelSchema):
    area_venta: Optional[AreaVentaSchema] = None

    class Meta:
        model = User
        fields = ["id", "username", "rol", "almacen"]


class EntradaAlmacenCafeteriaSchema(ModelSchema):
    info_producto: ProductoInfoSchema
    usuario: UsuariosSchema

    class Meta:
        model = Entradas_Cafeteria
        fields = "__all__"


class EntradaAlmacenCafeteriaEndpoint(Schema):
    entradas: List[EntradaAlmacenCafeteriaSchema]
    productos: List[ProductoParaEntradaAlmacenCafeteriaSchema]


class ProductoCodigoSchema(Schema):
    id: int
    codigo: str
    categoria: CategoriasSchema


class AddEntradaSchema(Schema):
    metodoPago: str
    proveedor: str
    variantes: Optional[List[VariantesSchema]] = None
    cantidad: Optional[int] = None
    productInfo: str
    comprador: str


class AddEntradaCafeteria(Schema):
    metodoPago: METODO_PAGO
    proveedor: str
    cantidad: Annotated[int, Field(strict=True, gt=0)]
    producto: str
    comprador: str


class AreaVentaModifySchema(ModelSchema):
    class Meta:
        model = AreaVenta
        exclude = ("id",)


class Salidas(Schema):
    id: int
    area_venta__nombre: Optional[str] = None
    usuario__username: Optional[str] = None
    producto__info__descripcion: Optional[str] = None
    created_at: datetime.datetime
    cantidad: int

    @validator("area_venta__nombre", pre=True, always=True)
    def set_default_area_venta(cls, v):
        return v or "Almacén Revoltosa"


class SalidaAlmacenSchema(Schema):
    salidas: List[Salidas]
    areas_de_venta: List[AreaVentaSchema]
    productos: List[ProductoCodigoSchema]


class SalidaAlmacenRevoltosaSchema(Schema):
    id: int
    usuario__username: str | None
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


class AddSalidaCafeteriaSchema(Schema):
    producto: int
    cantidad: Annotated[int, Field(strict=True, gt=0)]


class VentasSchema(Schema):
    id: int
    created_at: datetime.datetime
    importe: Decimal | None
    metodo_pago: str
    usuario__username: str | None
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
    tarjeta: Optional[int] = None

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

    @validator("tarjetas", pre=True, always=True, check_fields=False)
    def check_tarjeta(cls, v, values, **kwargs):
        if (
            values.get("metodoPago") == "MIXTO"
            or values.get("metodoPago") == METODO_PAGO.TRANSFERENCIA
        ):
            if v is None:
                raise ValueError("Debe seleccionar una tarjeta")
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
    precio_venta: Optional[condecimal(gt=0)] = None
    importe: Optional[condecimal(gt=0)] = None


class ProductoInfoParaReporte(Schema):
    id: int
    descripcion: str
    codigo: Optional[str] = None
    cantidad: Decimal
    precio_venta: Optional[condecimal(gt=0)] = None
    importe: Optional[condecimal(gt=0)] = None


class ReportesSchema(Schema):
    productos: List[ProductoInfoParaReporte]
    area: str
    total: Optional[condecimal()] = None
    pago_trabajador: Optional[conint(ge=0)] = None
    gastos_variables: Optional[Annotated[int, Field(ge=0)]] = None
    gastos_fijos: Optional[Annotated[int, Field(ge=0)]] = None
    costo_producto: Optional[condecimal()] = None
    subtotal: Optional[condecimal(ge=0)] = None
    efectivo: Optional[condecimal(ge=0)] = None
    transferencia: Optional[condecimal(ge=0)] = None


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


class Almacenes(Schema):
    inventario: InventarioSchema
    categorias: List[CategoriasSchema]


class AlmacenCafeteria(Schema):
    productos: List[OtrosProductos]
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


class GetUsuariosSchema(Schema):
    usuarios: List[UsuariosSchema]
    areas_ventas: List[AreaVentaSchema]


class UsuariosAuthSchema(ModelSchema):
    area_venta: Optional[int] = None
    almacen: Optional[str] = None

    class Meta:
        model = User
        fields = ["username", "password", "rol"]

    @validator("area_venta", "almacen", pre=True, always=True)
    def validate_area_venta_or_almacen(cls, v, values, **kwargs):
        if values.get("rol") == RolesChoices.VENDEDOR:
            if v is None:
                raise ValueError("area_venta debe tener valor si rol es vendedor")
        elif values.get("rol") == RolesChoices.ALMACENERO:
            if v is None:
                raise ValueError("almacen debe tener valor si rol es almacenero")
        return v


class Otros(Schema):
    area: str
    cantidad: int


class newZapatos(Schema):
    id: int
    info__codigo: Optional[str] = None
    color: str
    numero: int


class ZapatosForSearch(Schema):
    area: str
    productos: List[newZapatos]


class SearchProductSchema(Schema):
    info: Optional[ProductoInfoSchema] = None
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
    total_zapatos: int


class ProductosDentroDeTransferencia(Schema):
    descripcion: str
    total_transfers: int


class TransferenciaSchema(ModelSchema):
    usuario: Optional[UsuariosSchema] = None
    de: Optional[AreaVentaSchema] = None
    para: Optional[AreaVentaSchema] = None
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
    usuario: Optional[UsuariosSchema] = None
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


class GastosSchema(ModelSchema):
    usuario: Optional[UsuariosSchema] = None
    area_venta: Optional[AreaVentaSchema] = None

    class Meta:
        model = Gastos
        fields = "__all__"


class AllGastosSchema(Schema):
    fijos: List[GastosSchema]
    variables: List[GastosSchema]
    areas_venta: List[AreaVentaSchema]


class GastosModifySchema(Schema):
    descripcion: str
    tipo: GastosChoices
    area_venta: int | Literal["cafeteria"]
    cantidad: Annotated[int, Field(strict=True, gt=0)]
    frecuencia: Optional[FrecuenciaChoices] = None
    dia_semana: Optional[Annotated[int, Field(strict=True, ge=0, le=6)]] = None
    dia_mes: Optional[Annotated[int, Field(strict=True, ge=1, le=31)]] = None


class BalanceTarjetasSchema(ModelSchema):
    class Meta:
        model = BalanceTarjetas
        fields = "__all__"


class TarjetasWithTotalMESyDIASchema(Schema):
    id: int
    balance: BalanceTarjetasSchema
    nombre: str
    banco: str


class TarjetasForVentas(Schema):
    id: int
    nombre: str
    banco: str


class TarjetasSchema(ModelSchema):
    balance: BalanceTarjetasSchema

    class Meta:
        model = Tarjetas
        fields = "__all__"


class TarjetasModifySchema(Schema):
    nombre: str
    banco: BancoChoices
    saldo_inicial: str


class TransferenciasTarjetasSchema(ModelSchema):
    tarjeta: TarjetasSchema
    usuario: Optional[UsuariosSchema] = None

    class Meta:
        model = TransferenciasTarjetas
        fields = "__all__"


class TransferenciasTarjetasModify(Schema):
    tarjeta: int
    cantidad: str
    descripcion: str
    tipo: str


class TarjetasEndpoint(Schema):
    tarjetas: List[TarjetasWithTotalMESyDIASchema]
    transferencias: List[TransferenciasTarjetasSchema]


class OneAreaVentaSchema(Schema):
    inventario: InventarioAreaVentaSchema
    ventas: List[VentasSchema]
    area_venta: str
    all_productos: List[ProductoInfoSchema]
    tarjetas: List[TarjetasForVentas]


class Inventario_Almacen_Cafeteria_Schema(ModelSchema):
    class Meta:
        model = Inventario_Almacen_Cafeteria
        fields = "id", "cantidad"


class Producto_Cafeteria_Schema(ModelSchema):
    inventario_almacen: Inventario_Almacen_Cafeteria_Schema

    class Meta:
        model = Productos_Cafeteria
        fields = "__all__"


class Inventario_Area_Cafeteria_Schema(ModelSchema):
    class Meta:
        model = Inventario_Area_Cafeteria
        fields = "id", "cantidad"


class Producto_Cafeteria_Area_Schema(ModelSchema):
    inventario_area: Inventario_Almacen_Cafeteria_Schema

    class Meta:
        model = Productos_Cafeteria
        fields = "__all__"


class User_Only_Username(Schema):
    username: str


class Productos_Entrada_Cafeteria(Schema):
    id: int
    nombre: str


class Productos_Ventas_Cafeteria(Schema):
    producto: Productos_Entrada_Cafeteria
    cantidad: Decimal


class Elaboraciones_Ventas_Cafeteria(Schema):
    producto: Productos_Entrada_Cafeteria
    cantidad: Decimal


class Ventas_Cafeteria_Schema(ModelSchema):
    usuario: Optional[User_Only_Username] = None
    productos: List[Productos_Ventas_Cafeteria]
    elaboraciones: List[Elaboraciones_Ventas_Cafeteria]
    importe: Decimal
    tarjeta: Optional[str] = None

    class Meta:
        model = Ventas_Cafeteria
        fields = "__all__"


class TarjetasVentasCafeteriaSchema(Schema):
    id: int
    nombre: str
    banco: str


class Productos_Elaboraciones_Schema(Schema):
    id: int
    nombre: str
    isElaboracion: bool


class EndPointCafeteria(Schema):
    inventario: List[Producto_Cafeteria_Area_Schema]
    ventas: List[Ventas_Cafeteria_Schema]
    productos_elaboraciones: List[Productos_Elaboraciones_Schema]
    tarjetas: List[TarjetasVentasCafeteriaSchema]


class Producto_Entrada(Schema):
    id: int
    nombre: str


class Productos_Inside_Entradas(Schema):
    id: int
    producto: Producto_Entrada
    cantidad: Decimal


class Entradas_CafeteriaSchema(ModelSchema):
    usuario: Optional[User_Only_Username] = None
    productos: List[Productos_Inside_Entradas]

    class Meta:
        model = Entradas_Cafeteria
        fields = "__all__"


class Entradas_Almacen_Cafeteria_Schema(Schema):
    entradas: List[Entradas_CafeteriaSchema]
    productos: List[Productos_Entrada_Cafeteria]


class Add_Entrada_Cafeteria_Productos(Schema):
    producto: int
    cantidad: str


class Add_Entrada_Cafeteria(Schema):
    proveedor: str
    comprador: str
    metodo_pago: METODO_PAGO
    productos: List[Add_Entrada_Cafeteria_Productos]


class Producto_Cafeteria_Endpoint_Schema(Schema):
    id: int
    nombre: str
    precio_costo: Annotated[Decimal, Field(strict=True, ge=0)]
    precio_venta: Annotated[Decimal, Field(strict=True, ge=0)]


class Add_Producto_Cafeteria(Schema):
    nombre: str
    precio_costo: str
    precio_venta: str


class Ingrediente_Cantidad_Schema(Schema):
    ingrediente: Productos_Entrada_Cafeteria
    cantidad: Decimal


class ElaboracionesSchema(ModelSchema):
    ingredientes_cantidad: List[Ingrediente_Cantidad_Schema]

    class Meta:
        model = Elaboraciones
        fields = "__all__"


class ElaboracionesEndpoint(Schema):
    elaboraciones: List[ElaboracionesSchema]
    productos: List[Productos_Entrada_Cafeteria]


class IngredienteSchema(Schema):
    producto: int
    cantidad: str


class Add_Elaboracion(Schema):
    nombre: str
    precio: str
    mano_obra: str
    ingredientes: List[IngredienteSchema]


class Ventas_Cafeteria_Endpoint(Schema):
    ventas: List[Ventas_Cafeteria_Schema]
    productos_elaboraciones: List[Productos_Elaboraciones_Schema]
    tarjetas: List[TarjetasVentasCafeteriaSchema]


class Prod_Add_Venta(Schema):
    producto: int
    cantidad: str
    isElaboracion: bool


class Add_Venta_Cafeteria(Schema):
    metodo_pago: METODO_PAGO
    transferencia: Optional[str] = None
    efectivo: Optional[str] = None
    tarjeta: Optional[int] = None
    productos: List[Prod_Add_Venta]


class Productos_Reportes_Cafeteria(ModelSchema):
    cantidad: Decimal
    importe: Decimal

    class Meta:
        model = Productos_Cafeteria
        fields = "__all__"


class Elaboraciones_Reportes_Cafeteria(ModelSchema):
    cantidad: Decimal
    importe: Decimal

    class Meta:
        model = Elaboraciones
        fields = "__all__"


class CafeteriaReporteSchema(Schema):
    productos: List[Productos_Reportes_Cafeteria]
    elaboraciones: List[Elaboraciones_Reportes_Cafeteria]
    total: Decimal
    costo_producto: Decimal
    subtotal: Decimal
    efectivo: Decimal
    transferencia: Decimal
    merma: Decimal
    cuenta_casa: Decimal
    mano_obra: Decimal
    gastos_variables: Decimal
    gastos_fijos: Decimal


class Producto_Salida_Schema(Schema):
    producto: Producto_Entrada
    cantidad: Decimal


class Elaboraciones_Salida_Schema(Schema):
    producto: ElaboracionesSchema
    cantidad: Decimal


class Salidas_Almacen_Cafeteria_Schema(ModelSchema):
    usuario: Optional[User_Only_Username] = None
    productos: List[Producto_Salida_Schema]
    elaboraciones: List[Elaboraciones_Salida_Schema]

    class Meta:
        model = Salidas_Cafeteria
        fields = "__all__"


class EndPointSalidasAlmacenCafeteria(Schema):
    salidas: List[Salidas_Almacen_Cafeteria_Schema]
    productos_elaboraciones: List[Productos_Elaboraciones_Schema]


class Add_Salida_Cafeteria(Schema):
    productos: List[Prod_Add_Venta]


class MermaSchema(ModelSchema):
    usuario: Optional[UsuariosSchema] = None
    productos: List[Producto_Salida_Schema]
    elaboraciones: List[Elaboraciones_Salida_Schema]
    cantidad_productos: int
    cantidad_elaboraciones: int

    class Meta:
        model = MermaCafeteria
        fields = "__all__"


class EndpointMerma(Schema):
    productos_elaboraciones: List[Productos_Elaboraciones_Schema]
    merma: List[MermaSchema]


class AddMerma(Schema):
    localizacion: Literal["almacen-cafeteria", "cafeteria"]
    productos: List[Prod_Add_Venta]


class CuentaCasaSchema(ModelSchema):
    usuario: Optional[UsuariosSchema] = None
    productos: List[Producto_Salida_Schema]
    elaboraciones: List[Elaboraciones_Salida_Schema]
    cantidad_productos: int
    cantidad_elaboraciones: int

    class Meta:
        model = CuentaCasa
        fields = "__all__"


class EndpointCuentaCasa(Schema):
    productos_elaboraciones: List[Productos_Elaboraciones_Schema]
    cuenta_casa: List[CuentaCasaSchema]
