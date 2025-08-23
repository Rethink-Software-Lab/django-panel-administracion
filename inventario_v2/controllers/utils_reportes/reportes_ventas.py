from datetime import date
from decimal import Decimal

from django.db.models import (
    F,
    Q,
    Case,
    Count,
    ExpressionWrapper,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
    When,
    DecimalField,
    IntegerField,
)
from django.db.models.base import Coalesce
from django.shortcuts import get_object_or_404

from inventario.models import (
    CuentasChoices,
    FrecuenciaChoices,
    Gastos,
    GastosChoices,
    HistorialPrecioCostoSalon,
    HistorialPrecioVentaSalon,
    ProductoInfo,
    TipoTranferenciaChoices,
    Ventas,
    AreaVenta,
)
from inventario_v2.utils import (
    calcular_dias_laborables,
    obtener_dias_semana_rango,
    obtener_ultimo_dia_mes,
)


def get_gastos_varriables(
    parse_desde: date, parse_hasta: date, area: str
) -> QuerySet[Gastos]:
    filtros_gastos_variables = {
        "tipo": GastosChoices.VARIABLE,
        "created_at__date__range": (parse_desde, parse_hasta),
    }

    if area != "general":
        filtros_gastos_variables["area_venta"] = area

    gastos_variables = Gastos.objects.filter(**filtros_gastos_variables).only(
        "descripcion", "cantidad"
    )

    return gastos_variables


def get_reporte_ventas(parse_desde: date, parse_hasta: date, area: str):
    dias_laborables = calcular_dias_laborables(parse_desde, parse_hasta)
    ultimo_dia_hasta = obtener_ultimo_dia_mes(parse_hasta)
    dias_semana = obtener_dias_semana_rango(parse_desde, parse_hasta)

    filtros_gastos_variables = {
        "tipo": GastosChoices.VARIABLE,
        "created_at__date__range": (parse_desde, parse_hasta),
    }

    if area != "general":
        filtros_gastos_variables["area_venta"] = area

    gastos_variables = Gastos.objects.filter(**filtros_gastos_variables).only(
        "descripcion", "cantidad"
    )

    filtros_gastos_fijos = {
        "tipo": GastosChoices.FIJO,
        "created_at__date__lte": parse_hasta,
    }

    if area != "general":
        filtros_gastos_fijos["area_venta"] = area
        filtros_gastos_fijos["is_cafeteria"] = False

    gastos_fijos_result = Gastos.objects.filter(**filtros_gastos_fijos).annotate(
        dia_mes_ajustado=Case(
            When(dia_mes__gt=ultimo_dia_hasta, then=ultimo_dia_hasta),
            default=F("dia_mes"),
            output_field=IntegerField(),
        )
    )

    gastos_fijos = []

    for gasto in gastos_fijos_result:
        if (
            gasto.frecuencia == FrecuenciaChoices.MENSUAL
            and gasto.dia_mes_ajustado in range(parse_desde.day, parse_hasta.day + 1)
        ):
            gastos_fijos.append(
                {
                    "descripcion": gasto.descripcion,
                    "cantidad": gasto.cantidad,
                }
            )
        elif (
            gasto.frecuencia == FrecuenciaChoices.SEMANAL
            and gasto.dia_semana in dias_semana
        ):
            gastos_fijos.append(
                {
                    "descripcion": gasto.descripcion,
                    "cantidad": gasto.cantidad * dias_semana.get(gasto.dia_semana, 0),
                }
            )
        elif gasto.frecuencia == FrecuenciaChoices.LUNES_SABADO:
            gastos_fijos.append(
                {
                    "descripcion": gasto.descripcion,
                    "cantidad": gasto.cantidad * dias_laborables,
                }
            )

    filtros_productos = {
        "producto__venta__created_at__date__range": (
            parse_desde,
            parse_hasta,
        ),
        "producto__ajusteinventario__isnull": True,
    }

    if area != "general":
        filtros_productos["producto__area_venta"] = area

    productos_info_qs = ProductoInfo.objects.filter(**filtros_productos)

    historico_costo = (
        HistorialPrecioCostoSalon.objects.filter(
            producto_info=OuterRef("pk"),
            fecha_inicio__lte=OuterRef("producto__venta__created_at"),
        )
        .order_by("-fecha_inicio")
        .values("precio")[:1]
    )

    alternative_historico_costo = (
        HistorialPrecioCostoSalon.objects.filter(
            producto_info=OuterRef("pk"),
        )
        .order_by("-fecha_inicio")
        .values("precio")[:1]
    )

    historico_venta = (
        HistorialPrecioVentaSalon.objects.filter(
            producto_info=OuterRef("pk"),
            fecha_inicio__lte=OuterRef("producto__venta__created_at"),
        )
        .order_by("-fecha_inicio")
        .values("precio")[:1]
    )

    alternative_historico_venta = (
        HistorialPrecioVentaSalon.objects.filter(
            producto_info=OuterRef("pk"),
        )
        .order_by("-fecha_inicio")
        .values("precio")[:1]
    )

    productos_info_qs = productos_info_qs.annotate(
        precio_c=Coalesce(
            Subquery(historico_costo), Subquery(alternative_historico_costo)
        ),
        precio_v=Coalesce(
            Subquery(historico_venta), Subquery(alternative_historico_venta)
        ),
    )

    producto_info = (
        productos_info_qs.annotate(
            cantidad=Count("producto"),
            importe=ExpressionWrapper(
                F("cantidad") * F("precio_v"), output_field=DecimalField()
            ),
            costo=ExpressionWrapper(
                F("cantidad") * F("precio_c"), output_field=DecimalField()
            ),
        )
        .values(
            "id",
            "importe",
            "costo",
            "cantidad",
            "descripcion",
            precio_venta=F("precio_v"),
            precio_costo=F("precio_c"),
        )
        .order_by("-importe")
    )

    productos_agrupados = {}

    for producto in producto_info:
        producto_id = producto["id"]
        if producto_id not in productos_agrupados:
            productos_agrupados[producto_id] = {
                "id": producto_id,
                "descripcion": producto["descripcion"],
                "cantidad": Decimal(0),
                "importe": Decimal(0),
                "precio_costo": producto.get("precio_costo"),
                "precio_venta": producto.get("precio_venta"),
            }

        productos_agrupados[producto_id]["cantidad"] += Decimal(
            str(producto.get("cantidad", 0) or 0)
        )
        productos_agrupados[producto_id]["importe"] += Decimal(
            str(producto.get("importe", 0) or 0)
        )

    productos_sin_repeticion = list(productos_agrupados.values())

    filtros_ventas: dict[str, str | tuple[date, date]] = {
        "created_at__date__range": (parse_desde, parse_hasta)
    }

    if area != "general":
        filtros_ventas["area_venta__id"] = area

    if area != "general":
        area_venta = get_object_or_404(AreaVenta, pk=area)

    total_gastos_fijos = sum(gasto.get("cantidad", 0) for gasto in gastos_fijos)

    ventas = Ventas.objects.filter(**filtros_ventas).annotate(
        productos_count=Count("producto"),
        pago_trabajador_total=ExpressionWrapper(
            F("producto__info__pago_trabajador") * F("productos_count"),
            output_field=DecimalField(),
        ),
        efectivo_total=Sum(
            "transacciones__cantidad",
            filter=Q(
                transacciones__tipo=TipoTranferenciaChoices.INGRESO,
                transacciones__cuenta__tipo=CuentasChoices.EFECTIVO,
            ),
            output_field=DecimalField(),
        ),
    )

    subtotales = ventas.aggregate(
        subtotal_efectivo=Sum(
            ExpressionWrapper(
                F("efectivo_total") + F("pago_trabajador_total"),
                output_field=DecimalField(),
            )
        ),
        subtotal_transferencia=Sum(
            "transacciones__cantidad",
            filter=Q(
                transacciones__tipo=TipoTranferenciaChoices.INGRESO,
                transacciones__cuenta__tipo=CuentasChoices.BANCARIA,
            ),
            output_field=DecimalField(),
        ),
    )

    subtotal = producto_info.aggregate(subtotal=Sum("importe"))["subtotal"] or 0
    costo_productos = (
        producto_info.aggregate(costo_productos=Sum("costo"))["costo_productos"] or 0
    )

    pago_trabajador = (
        producto_info.aggregate(
            pago_trabajador=Sum(F("pago_trabajador") * F("cantidad"))
        )["pago_trabajador"]
        or 0
    )

    ventas_por_usuario = {}

    prod = producto_info.annotate(
        usuario=F("producto__venta__usuario__username"),
        pago=F("pago_trabajador") * F("cantidad"),
    )
    for producto in prod:
        usuario = producto.get("usuario") or "Sin usuario"

        if usuario not in ventas_por_usuario:
            ventas_por_usuario[usuario] = 0

        ventas_por_usuario[usuario] += producto.get("pago", 0)

    monto_gastos_variables = (
        gastos_variables.aggregate(total=Sum("cantidad"))["total"] or 0
    ) + pago_trabajador

    total_gatos = total_gastos_fijos + monto_gastos_variables or 0

    total = subtotal - total_gatos

    ganancia = total - costo_productos

    return {
        "productos": productos_sin_repeticion,
        "subtotal": {
            "general": subtotal,
            "efectivo": subtotales.get("subtotal_efectivo", 0),
            "transferencia": subtotales.get("subtotal_transferencia", 0),
        },
        "gastos_fijos": gastos_fijos,
        "gastos_variables": gastos_variables,
        "pago_trabajador": round(pago_trabajador, 2),
        "ventas_por_usuario": ventas_por_usuario,
        "total": {
            "general": total,
            "efectivo": subtotales.get("subtotal_efectivo", 0) - total_gatos,
            "transferencia": subtotales.get("subtotal_transferencia", 0),
        },
        "ganancia": ganancia,
        "area": area_venta.nombre if area != "general" else "general",
    }
