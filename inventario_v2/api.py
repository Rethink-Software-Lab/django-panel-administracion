from ninja.errors import HttpError

from .schema import SearchProductSchema, LoginSchema, TokenSchema
from inventario.models import ProductoInfo, Producto, AreaVenta, User
from ninja.security import HttpBearer
import jwt
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError
from django.conf import settings
from ninja_extra import NinjaExtraAPI
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta

from inventario_v2.controllers.categorias import CategoriasController
from inventario_v2.controllers.entradas import EntradasController
from inventario_v2.controllers.graficas import GraficasController
from inventario_v2.controllers.salidas import SalidasController
from inventario_v2.controllers.salidas_revoltosa import SalidasRevoltosaController
from inventario_v2.controllers.ventas import VentasController
from inventario_v2.controllers.inventario import InventarioController
from inventario_v2.controllers.productos import ProductoController
from inventario_v2.controllers.usuarios import UsuariosController
from inventario_v2.controllers.reportes import ReportesController
from .controllers.areas_ventas import AreasVentasController
from .controllers.transferencias import TransferenciasController
from .controllers.ajuste_inventario import AjusteInventarioController
from .controllers.gastos import GastosController
from .controllers.tarjetas import TarjetasController
from .controllers.cafeteria import CafeteriaController


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except InvalidSignatureError:
            raise HttpError(498, "Token corrupto")
        except ExpiredSignatureError:
            raise HttpError(498, "Token expirado")
        except:
            return request
        return {"id": payload["id"], "rol": payload["rol"]}


app = NinjaExtraAPI(
    auth=AuthBearer(),
    openapi_extra={
        "info": {
            "termsOfService": "https://example.com/terms/",
        }
    },
    title="Inventario",
)


@app.post("login/", auth=None, response=TokenSchema)
def login(request, data: LoginSchema):
    dataMD = data.model_dump()
    username = dataMD["username"]
    password = dataMD["password"]
    try:
        user = User.objects.get(username=username)

    except User.DoesNotExist:
        raise HttpError(401, "Credenciales inválidas")

    passOk = user.check_password(password)
    if passOk:
        payload = {
            "id": user.pk,
            "rol": user.rol,
            "area_venta": user.area_venta.pk if user.area_venta else None,
            "almacen": user.almacen,
            "exp": datetime.utcnow() + timedelta(weeks=4),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {"token": token}
    else:
        raise HttpError(401, "Credenciales inválidas")


# TODO: Dividir info_producto y tabla_producto
@app.get("search/{codigo}/", response=SearchProductSchema, tags=["Buscar Producto"])
def search_product(request, codigo: str):
    areas = AreaVenta.objects.all().values("id", "nombre")
    info = get_object_or_404(ProductoInfo, codigo=codigo)
    dataDict = []
    for area in areas:
        if info.categoria.nombre == "Zapatos":
            data = Producto.objects.filter(
                venta__isnull=True,
                info__categoria__nombre="Zapatos",
                info__codigo=codigo,
                area_venta=area["id"],
                ajusteinventario__isnull=True,
            ).values("id", "color", "numero")
            if len(data) > 0:
                dataDict.append({"area": area["nombre"], "productos": data})
        else:
            data = Producto.objects.filter(
                venta__isnull=True,
                info__codigo=codigo,
                area_venta=area["id"],
                ajusteinventario__isnull=True,
            ).count()
            if data > 0:
                dataDict.append({"area": area["nombre"], "cantidad": data})

    if info.categoria.nombre == "Zapatos":
        productos_almacen = Producto.objects.filter(
            venta__isnull=True,
            info__codigo=codigo,
            area_venta__isnull=True,
            info__categoria__nombre="Zapatos",
            ajusteinventario__isnull=True,
        ).values("id", "color", "numero")
        if productos_almacen.count() > 0:
            dataDict.append({"area": "Almacén", "productos": productos_almacen})
    else:
        productos_almacen = (
            Producto.objects.filter(
                venta__isnull=True,
                info__codigo=codigo,
                area_venta__isnull=True,
                ajusteinventario__isnull=True,
            )
            .exclude(info__categoria__nombre="Zapatos")
            .count()
        )
        if productos_almacen > 0:
            dataDict.append({"area": "Almacén", "cantidad": productos_almacen})

    return {
        "info": info,
        "zapato": info.categoria.nombre == "Zapatos",
        "inventario": dataDict[::-1],
    }


app.register_controllers(
    CategoriasController,
    EntradasController,
    GraficasController,
    SalidasController,
    SalidasRevoltosaController,
    VentasController,
    InventarioController,
    ProductoController,
    UsuariosController,
    ReportesController,
    AreasVentasController,
    TransferenciasController,
    AjusteInventarioController,
    GastosController,
    TarjetasController,
    CafeteriaController,
)
