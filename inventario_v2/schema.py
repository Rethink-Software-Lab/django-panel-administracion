import datetime
from ninja import ModelSchema, Schema
from inventario.models import *
from typing import List, Optional, Literal, Any, Dict
from pydantic import condecimal, conint, validator, Field, model_validator
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
    precio_costo: Optional[Decimal] = None
    precio_venta: Optional[Decimal] = None

    class Meta:
        model = ProductoInfo
        fields = "__all__"


class TarjetasSchema(ModelSchema):
    class Meta:
        model = Cuentas
        fields = "__all__"


class ResponseEntradasPrinciapl(Schema):
    productos: List[ProductoInfoSchema]
    cuentas: List[TarjetasSchema]


class ProductoSchema(ModelSchema):
    info: ProductoInfoSchema

    class Meta:
        model = Producto
        fields = "__all__"


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


class ProductoCodigoSchema(Schema):
    id: int
    descripcion: str
    categoria: CategoriasSchema


class ProductosEntradaAlmacenPrincipal(Schema):
    producto: str
    cantidad: Optional[int] = None
    isZapato: bool
    variantes: Optional[List[VariantesSchema]] = None

    @model_validator(mode="after")
    def check_variantes_if_zapato(self):
        if self.isZapato and (not self.variantes or len(self.variantes) == 0):
            raise ValueError(
                "Si 'isZapato' es True, 'variantes' debe ser proporcionado y no estar vacío."
            )
        return self


class EntradaAlmacenSchema(Schema):
    id: int
    metodo_pago: str
    nombre_proveedor: Optional[str] = None
    comprador: str
    username: Optional[str] = None
    fecha: datetime.datetime


class CuentasInCreateEntrada(Schema):
    cuenta: str
    cantidad: Optional[Decimal] = None


class AddEntradaSchema(Schema):
    metodoPago: str
    proveedor: str
    productos: List[ProductosEntradaAlmacenPrincipal]
    comprador: str
    cuentas: Annotated[List[CuentasInCreateEntrada], Field(min_length=1)]

    @model_validator(mode="after")
    def validar_cuentas(self):
        if len(self.cuentas) != 1:
            for c in self.cuentas:
                if c.cantidad is None:
                    raise ValueError(
                        "Cuando hay varias cuentas, todas deben tener cantidad."
                    )

        return self


class ResponseNumeros(Schema):
    numero: int
    ids: str


class ResponseVariantes(Schema):
    color: str
    numeros: List[ResponseNumeros]


class ResponseAddEntrada(Schema):
    zapato: str
    variantes: List[ResponseVariantes]


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


class SalidaAlmacenRevoltosaSchema(Schema):
    id: int
    usuario__username: str | None
    producto__info__descripcion: str | None
    created_at: datetime.datetime
    cantidad: int


class ProductoInfoSalidaAlmacenRevoltosaSchema(Schema):
    salidas: List[SalidaAlmacenRevoltosaSchema]
    productos: List[ProductoCodigoSchema]


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


class OtrosProductos(Schema):
    id: int
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
    cantidad: Decimal
    precio_venta: Optional[Annotated[Decimal, Field(gt=0)]] = None
    importe: Optional[Decimal] = None


class SubtotalReporteVentas(Schema):
    general: Decimal
    efectivo: Decimal
    transferencia: Decimal


class GastosReporte(Schema):
    descripcion: str
    cantidad: int


class TotalReporte(Schema):
    general: Decimal
    efectivo: Decimal
    transferencia: Decimal


class ReportesSchema(Schema):
    productos: List[ProductoInfoParaReporte]
    area: str
    total: Optional[TotalReporte] = None
    pago_trabajador: Optional[Annotated[int, Field(ge=0)]] = None
    ventas_por_usuario: Optional[Dict[str, Annotated[int, Field(ge=0)]]] = None
    gastos_variables: Optional[List[GastosReporte]] = None
    gastos_fijos: Optional[List[GastosReporte]] = None
    costo_producto: Optional[Decimal] = None
    subtotal: Optional[SubtotalReporteVentas] = None
    ganancia: Optional[Decimal] = None


class Zapatos(Schema):
    id: int
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
    descripcion: str
    categoria: int
    precio_costo: Annotated[Decimal, Field(gt=0)]
    precio_venta: Annotated[Decimal, Field(gt=0)]
    pago_trabajador: Annotated[int, Field(ge=0)]


class UpdateProductoSchema(Schema):
    descripcion: str
    categoria: int
    pago_trabajador: Annotated[int, Field(ge=0)]
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
    color: str
    numero: int


class ZapatosForSearch(Schema):
    area: str
    productos: List[newZapatos]


class SearchProductSchema(Schema):
    info: Optional[ProductoInfoSchema] = None
    zapato: bool
    inventario: List[Otros] | List[ZapatosForSearch]


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


class TarjetasForVentas(Schema):
    id: int
    nombre: str
    banco: str
    disponible: bool


class TarjetasModifySchema(Schema):
    nombre: str
    tipo: CuentasChoices
    banco: BancoChoices
    saldo_inicial: str


class TransferenciasTarjetasModify(Schema):
    cuenta: int
    cantidad: str
    descripcion: str
    tipo: str


class Inventario_Almacen_Cafeteria_Schema(ModelSchema):
    class Meta:
        model = Inventario_Almacen_Cafeteria
        fields = "id", "cantidad"


class Producto_Cafeteria_Schema(ModelSchema):
    inventario_almacen: Inventario_Almacen_Cafeteria_Schema
    precio_venta: Decimal

    class Meta:
        model = Productos_Cafeteria
        fields = "__all__"


class Inventario_Area_Cafeteria_Schema(ModelSchema):
    class Meta:
        model = Inventario_Area_Cafeteria
        fields = "id", "cantidad"


class Producto_Cafeteria_Area_Schema(ModelSchema):
    inventario_area: Inventario_Almacen_Cafeteria_Schema
    precio_venta: Decimal

    class Meta:
        model = Productos_Cafeteria
        fields = "__all__"


class User_Only_Username(Schema):
    username: str


class Productos_Entrada_Cafeteria(Schema):
    id: int
    nombre: str
    precio_costo: Decimal
    precio_venta: Decimal


class Producto_In_Venta_Cafeteria(Schema):
    id: int
    nombre: str


class Productos_Ventas_Cafeteria(Schema):
    producto: Producto_In_Venta_Cafeteria
    cantidad: Decimal


class Elaboraciones_Ventas_Cafeteria(Schema):
    producto: Producto_In_Venta_Cafeteria
    cantidad: Decimal


class Ventas_Cafeteria_Schema(ModelSchema):
    usuario: Optional[str] = None
    productos: List[Productos_Ventas_Cafeteria]
    elaboraciones: List[Elaboraciones_Ventas_Cafeteria]
    importe: Annotated[Decimal, Field(gt=0)]
    cuenta: Optional[str] = None

    class Meta:
        model = Ventas_Cafeteria
        fields = "__all__"


class TarjetasVentasCafeteriaSchema(Schema):
    id: int
    nombre: str
    banco: str
    disponible: bool


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
    precio_costo: Decimal


class Productos_Inside_Entradas(Schema):
    id: int
    producto: Producto_Entrada
    cantidad: Decimal


class ProveedorSchema(ModelSchema):
    class Meta:
        model = Proveedor
        fields = "__all__"


class Entradas_CafeteriaSchema(ModelSchema):
    usuario: Optional[User_Only_Username] = None
    productos: List[Productos_Inside_Entradas]
    proveedor: Optional[ProveedorSchema] = None

    class Meta:
        model = Entradas_Cafeteria
        fields = "__all__"


class ProveedorEntradasCafeteria(ModelSchema):
    class Meta:
        model = Proveedor
        fields = ["id", "nombre"]


class Entradas_Almacen_Cafeteria_Schema(Schema):
    entradas: List[Entradas_CafeteriaSchema]
    productos: List[Productos_Entrada_Cafeteria]
    cuentas: List[TarjetasSchema]
    proveedores: List[ProveedorEntradasCafeteria]


class Add_Entrada_Cafeteria_Productos(Schema):
    producto: int
    cantidad: str
    precio_costo: Optional[str] = None
    precio_venta: Optional[str] = None


class Add_Entrada_Cafeteria(Schema):
    comprador: str
    metodo_pago: METODO_PAGO
    productos: List[Add_Entrada_Cafeteria_Productos]
    cuenta: str
    proveedor: Optional[str] = None
    proveedor_nombre: Optional[str] = None
    proveedor_nit: Optional[str] = None
    proveedor_telefono: Optional[str] = None
    proveedor_direccion: Optional[str] = None
    proveedor_no_cuenta_cup: Optional[str] = None
    proveedor_no_cuenta_mayorista: Optional[str] = None


class Producto_Cafeteria_Endpoint_Schema(Schema):
    id: int
    nombre: str
    precio_costo: Annotated[Decimal, Field(strict=True, ge=0)]
    precio_venta: Annotated[Decimal, Field(strict=True, ge=0)]


class Add_Producto_Cafeteria(Schema):
    nombre: str
    precio_costo: str
    precio_venta: str


class Edit_Producto_Cafeteria(Schema):
    nombre: str
    precio_costo: Optional[str] = None
    precio_venta: Optional[str] = None


class Ingrediente_Cantidad_Schema(Schema):
    ingrediente: Productos_Entrada_Cafeteria
    cantidad: Decimal


class ElaboracionesSchema(ModelSchema):
    ingredientes_cantidad: List[Ingrediente_Cantidad_Schema]
    precio: Annotated[Decimal, Field(ge=0)]

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
    transferencia: Optional[Annotated[Decimal, Field(gt=0)]] = None
    efectivo: Optional[Annotated[Decimal, Field(gt=0)]] = None
    tarjeta: Optional[int] = None
    productos: List[Prod_Add_Venta]


class Productos_Reportes_Cafeteria(ModelSchema):
    cantidad: Decimal
    importe: Decimal
    precio_venta: Optional[Decimal] = None

    class Meta:
        model = Productos_Cafeteria
        fields = "__all__"


class Elaboraciones_Reportes_Cafeteria(ModelSchema):
    precio_unitario: Annotated[Decimal, Field(ge=0)]
    cantidad: Decimal
    importe: Decimal

    class Meta:
        model = Elaboraciones
        fields = "__all__"


class SubtotalReporteCafeteria(Schema):
    general: Decimal
    efectivo: Decimal
    transferencia: Decimal


class TotalReporteCafeteria(Schema):
    general: Decimal
    efectivo: Decimal
    transferencia: Decimal


class GastosVariablesReporteCafeteria(Schema):
    descripcion: str
    cantidad: int


class GastosFijosReporteCafeteria(Schema):
    descripcion: str
    cantidad: int


class CafeteriaReporteSchema(Schema):
    productos: List[Productos_Reportes_Cafeteria]
    elaboraciones: List[Elaboraciones_Reportes_Cafeteria]
    total: TotalReporteCafeteria
    subtotal: SubtotalReporteCafeteria
    mano_obra: Decimal
    gastos_variables: List[GastosVariablesReporteCafeteria]
    gastos_fijos: List[GastosFijosReporteCafeteria]
    ganancia: Decimal


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


class NoRepresentadosSchema(Schema):
    id: int
    nombre: str
