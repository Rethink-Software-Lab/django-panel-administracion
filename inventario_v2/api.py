from typing import List
from ninja.errors import HttpError

from .schema import NoRepresentadosSchema, LoginSchema, TokenSchema
from inventario.models import ProductoInfo, User
from ninja.security import HttpBearer
import jwt
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError
from django.conf import settings
from ninja_extra import NinjaExtraAPI
from datetime import datetime, timedelta
from django.db.models import (
    Count,
    Q,
    F,
)


from inventario_v2.controllers.entradas import EntradasController
from inventario_v2.controllers.graficas import GraficasController
from inventario_v2.controllers.salidas import SalidasController
from inventario_v2.controllers.salidas_revoltosa import SalidasRevoltosaController
from inventario_v2.controllers.inventario import InventarioController
from inventario_v2.controllers.productos import ProductoController
from inventario_v2.controllers.usuarios import UsuariosController
from inventario_v2.controllers.reportes import ReportesController
from .controllers.transferencias import TransferenciasController
from .controllers.ajuste_inventario import AjusteInventarioController
from .controllers.tarjetas import TarjetasController
from .controllers.cafeteria import CafeteriaController
from .controllers.almacen_cafeteria import AlmacenCafeteriaController
from .controllers.merma import MermaController
from .controllers.cuenta_casa import CuentaCasaController


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
            "username": user.username,
            "rol": user.rol,
            "area_venta": user.area_venta.pk if user.area_venta else None,
            "almacen": user.almacen,
            "exp": datetime.utcnow() + timedelta(weeks=4),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {"token": token}
    else:
        raise HttpError(401, "Credenciales inválidas")


@app.get(
    "no-representados/", response=List[NoRepresentadosSchema], tags=["No Representados"]
)
def nR(request):
    productos_info_sin_ventas = (
        ProductoInfo.objects.select_related("producto")
        .annotate(
            productos_disp=Count(
                "producto",
                filter=Q(
                    producto__venta__isnull=True,
                    producto__area_venta__isnull=True,
                    producto__ajusteinventario__isnull=True,
                ),
            ),
            productos_area_venta=Count(
                "producto",
                filter=Q(
                    producto__venta__isnull=True,
                    producto__area_venta__isnull=False,
                    producto__ajusteinventario__isnull=True,
                ),
            ),
        )
        .filter(
            productos_disp__gt=0,
            productos_area_venta=0,
        )
        .values(
            "id",
            nombre=F("descripcion"),
        )
    )
    return productos_info_sin_ventas


app.register_controllers(
    EntradasController,
    GraficasController,
    SalidasController,
    SalidasRevoltosaController,
    InventarioController,
    ProductoController,
    UsuariosController,
    ReportesController,
    TransferenciasController,
    AjusteInventarioController,
    TarjetasController,
    CafeteriaController,
    AlmacenCafeteriaController,
    MermaController,
    CuentaCasaController,
)
