import calendar
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Counter

from inventario.models import Cuentas, TipoTranferenciaChoices
from django.db.models import Sum, Value, Q
from django.db.models.functions import Coalesce, Round
from django.http import Http404
from django.core.exceptions import ValidationError
from django.db.models import QuerySet


days_names = {
    0: "Lun",
    1: "Mar",
    2: "Mié",
    3: "Jue",
    4: "Vie",
    5: "Sáb",
    6: "Dom",
}


def get_day_name(day_number):
    return days_names.get(day_number, "Día no válido")


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


def calcular_dias_laborables(desde, hasta):
    delta = timedelta(days=1)
    dias_laborables = 0
    while desde <= hasta:
        if desde.weekday() != 6:
            dias_laborables += 1
        desde += delta
    return dias_laborables


def obtener_inicio_fin_mes(anio, mes):
    inicio_mes = datetime(anio, mes, 1)

    ultimo_dia = calendar.monthrange(anio, mes)[1]
    fin_mes = datetime(anio, mes, ultimo_dia)

    return inicio_mes, fin_mes


def obtener_ultimo_dia_mes(fecha):
    _, ultimo_dia = calendar.monthrange(fecha.year, fecha.month)
    return ultimo_dia


def obtener_dias_semana_rango(desde, hasta):
    dias_semana = Counter()
    while desde <= hasta:
        dias_semana[desde.weekday()] += 1
        desde += timedelta(days=1)
    return dias_semana


# MAX_TRANSF_MES = 120000
# MAX_TRANSF_DIA = 80000


# def validate_transferencia(id_tarjeta: int) -> Tarjetas | ValidationError | Http404:
#     qs_tarjeta = Tarjetas.objects.annotate(
#         total_transferencias_mes=Round(
#             Coalesce(
#                 Sum(
#                     "transferenciastarjetas__cantidad",
#                     filter=Q(
#                         transferenciastarjetas__created_at__month=datetime.now().month,
#                         transferenciastarjetas__tipo=TipoTranferenciaChoices.EGRESO,
#                     ),
#                 ),
#                 Value(Decimal(0)),
#             ),
#             2,
#         ),
#         total_transferencias_dia=Round(
#             Coalesce(
#                 Sum(
#                     "transferenciastarjetas__cantidad",
#                     filter=Q(
#                         transferenciastarjetas__created_at=datetime.now(),
#                         transferenciastarjetas__tipo=TipoTranferenciaChoices.EGRESO,
#                     ),
#                 ),
#                 Value(Decimal(0)),
#             ),
#             2,
#         ),
#     ).filter(pk=id_tarjeta)

#     tarjeta = qs_tarjeta.first()

#     if not tarjeta:
#         raise Http404("Tarjeta no encontrada")

#     total_transferencias_mes = getattr(tarjeta, "total_transferencias_mes", Decimal(0))
#     total_transferencias_dia = getattr(tarjeta, "total_transferencias_dia", Decimal(0))

#     if total_transferencias_mes >= MAX_TRANSF_MES:
#         raise ValidationError("Ha superado el límite de transferencias mensuales")

#     if total_transferencias_dia >= MAX_TRANSF_DIA:
#         raise ValidationError("Ha superado el límite de transferencias diarias")

#     return tarjeta
