from ninja.errors import HttpError

from .schema import *
from ninja.security import HttpBearer
import jwt
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError
from django.conf import settings
from ninja_extra import NinjaExtraAPI

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


app.register_controllers(
    CategoriasController, 
    EntradasController, 
    GraficasController, 
    SalidasController, 
    VentasController, 
    InventarioController, 
    ProductoController,
    UsuariosController
    )
