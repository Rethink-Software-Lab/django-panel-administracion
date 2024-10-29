import calendar
from datetime import datetime, timedelta
from typing import Counter


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
