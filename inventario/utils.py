from calendar import timegm
from datetime import datetime


month_names = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def get_month_name(month_number):
    return month_names.get(month_number, "Mes no válido")


def custom_jwt_payload(user, context=None):

    from project_inventario.settings import GRAPHQL_JWT as jwt_settings

    username = user.get_username()

    if hasattr(username, "pk"):
        username = username.pk

    exp = datetime.utcnow() + jwt_settings["JWT_EXPIRATION_DELTA"]

    payload = {
        user.USERNAME_FIELD: username,
        "exp": timegm(exp.utctimetuple()),
        "area_venta": user.area_venta.id if user.area_venta else None,
        "origIat": timegm(datetime.utcnow().utctimetuple()),
        "id": user.id,
        "rol": user.rol,
    }

    return payload
