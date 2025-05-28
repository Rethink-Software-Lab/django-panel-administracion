from decimal import Decimal
from typing import List, Optional
from ninja.errors import HttpError

from .schema import NoRepresentadosSchema, SearchProductSchema, LoginSchema, TokenSchema
from inventario.models import ProductoInfo, Producto, AreaVenta, User
from ninja.security import HttpBearer
import jwt
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError
from django.conf import settings
from ninja_extra import NinjaExtraAPI
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from django.db.models import (
    Count,
    Q,
    F,
)

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
                    producto__venta__isnull=True, producto__area_venta__isnull=True
                ),
            ),
            productos_area_venta=Count(
                "producto",
                filter=Q(
                    producto__venta__isnull=True, producto__area_venta__isnull=False
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


# TODO: Dividir info_producto y tabla_producto
@app.get("search/", response=SearchProductSchema, tags=["Buscar Producto"])
def search_product(request, id: Optional[int] = None):
    areas = AreaVenta.objects.all().values("id", "nombre")

    info = get_object_or_404(ProductoInfo, id=id)

    dataDict = []
    # if not codigo:
    #     for area in areas:
    #         data = Producto.objects.filter(
    #             venta__isnull=True,
    #             info__categoria__nombre="Zapatos",
    #             area_venta=area["id"],
    #             numero=numero,
    #             ajusteinventario__isnull=True,
    #         ).values("id", "info__codigo", "color", "numero")
    #         if len(data) > 0:
    #             dataDict.append({"area": area["nombre"], "productos": data})

    #     productos_almacen = Producto.objects.filter(
    #         venta__isnull=True,
    #         area_venta__isnull=True,
    #         info__categoria__nombre="Zapatos",
    #         ajusteinventario__isnull=True,
    #         numero=numero,
    #     ).values("id", "info__codigo", "color", "numero")
    #     if productos_almacen.count() > 0:
    #         dataDict.append({"area": "Almacén", "productos": productos_almacen})

    for area in areas:
        if info.categoria.nombre == "Zapatos":
            data = Producto.objects.filter(
                venta__isnull=True,
                info__categoria__nombre="Zapatos",
                info=info,
                area_venta=area["id"],
                ajusteinventario__isnull=True,
            ).values("id", "color", "numero")
            if len(data) > 0:
                dataDict.append({"area": area["nombre"], "productos": data})
        else:
            data = Producto.objects.filter(
                venta__isnull=True,
                info=info,
                area_venta=area["id"],
                ajusteinventario__isnull=True,
            ).count()
            if data > 0:
                dataDict.append({"area": area["nombre"], "cantidad": data})

    if info.categoria.nombre == "Zapatos":
        productos_almacen = Producto.objects.filter(
            venta__isnull=True,
            info=info,
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
                info=info,
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
        "zapato": info.categoria.nombre == "Zapatos" if info else True,
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
    AlmacenCafeteriaController,
    MermaController,
    CuentaCasaController,
)
