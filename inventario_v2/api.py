from ninja.errors import HttpError

from .schema import SearchProductSchema
from inventario.models import ProductoInfo, Producto, AreaVenta
from ninja.security import HttpBearer
import jwt
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError
from django.conf import settings
from ninja_extra import NinjaExtraAPI
from django.shortcuts import get_object_or_404

from inventario_v2.controllers.categorias import CategoriasController
from inventario_v2.controllers.entradas import EntradasController
from inventario_v2.controllers.graficas import GraficasController
from inventario_v2.controllers.salidas import SalidasController
from inventario_v2.controllers.ventas import VentasController
from inventario_v2.controllers.inventario import InventarioController
from inventario_v2.controllers.productos import ProductoController
from inventario_v2.controllers.usuarios import UsuariosController


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
            ).values("id", "color", "numero")
            if len(data) > 0:
                dataDict.append({"area": area["nombre"], "productos": data})
        else:
            data = Producto.objects.filter(
                venta__isnull=True, info__codigo=codigo, area_venta=area["id"]
            ).count()
            if data > 0:
                dataDict.append({"area": area["nombre"], "cantidad": data})

    if info.categoria.nombre == "Zapatos":
        productos_almacen = Producto.objects.filter(
            venta__isnull=True,
            info__codigo=codigo,
            area_venta__isnull=True,
            info__categoria__nombre="Zapatos",
        ).values("id", "color", "numero")
        if productos_almacen.count() > 0:
            dataDict.append({"area": "Almacén", "productos": productos_almacen})
    else:
        productos_almacen = (
            Producto.objects.filter(
                venta__isnull=True,
                info__codigo=codigo,
                area_venta__isnull=True,
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
    VentasController,
    InventarioController,
    ProductoController,
    UsuariosController,
)
