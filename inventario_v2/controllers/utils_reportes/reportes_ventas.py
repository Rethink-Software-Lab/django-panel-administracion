from datetime import date
from decimal import Decimal

from django.db.models import (
    F,
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
    Transacciones,
    Ventas,
    AreaVenta,
)
from inventario_v2.controllers.utils_reportes.reporte_ventas_cafeteria import (
    get_reporte_ventas_cafeteria,
)
from inventario_v2.utils import (
    calcular_dias_laborables,
    obtener_dias_semana_rango,
    obtener_ultimo_dia_mes,
)


def get_gastos_variables(
    parse_desde: date, parse_hasta: date, area: str
) -> QuerySet[Gastos]:
    filtros_gastos_variables = {
        "tipo": GastosChoices.VARIABLE,
        "created_at__date__range": (parse_desde, parse_hasta),
    }

    if area != "general":
        filtros_gastos_variables["areas_venta"] = area

    gastos_variables = Gastos.objects.filter(**filtros_gastos_variables).only(
        "descripcion", "cantidad"
    )

    return gastos_variables


def get_reporte_ventas(parse_desde: date, parse_hasta: date, area: str):
    dias_laborables = calcular_dias_laborables(parse_desde, parse_hasta)
    ultimo_dia_hasta = obtener_ultimo_dia_mes(parse_hasta)
    dias_semana = obtener_dias_semana_rango(parse_desde, parse_hasta)

    gastos_variables_queryset_sin_pago_trabajador = get_gastos_variables(
        parse_desde, parse_hasta, area
    )

    filtros_gastos_fijos = {
        "tipo": GastosChoices.FIJO,
        "created_at__date__lte": parse_hasta,
    }

    if area != "general":
        filtros_gastos_fijos["areas_venta"] = area
        filtros_gastos_fijos["is_cafeteria"] = False

    gastos_fijos_result = Gastos.objects.filter(**filtros_gastos_fijos).annotate(
        dia_mes_ajustado=Case(
            When(dia_mes__gt=ultimo_dia_hasta, then=ultimo_dia_hasta),
            default=F("dia_mes"),
            output_field=IntegerField(),
        ),
        cantidad_areas=Count("areas_venta"),
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
                    "cantidad": (gasto.cantidad / gasto.cantidad_areas)
                    if gasto.cantidad_areas != 0
                    else gasto.cantidad,
                }
            )
        elif (
            gasto.frecuencia == FrecuenciaChoices.SEMANAL
            and gasto.dia_semana in dias_semana
        ):
            gastos_fijos.append(
                {
                    "descripcion": gasto.descripcion,
                    "cantidad": (
                        gasto.cantidad
                        * dias_semana.get(gasto.dia_semana, 0)
                        / gasto.cantidad_areas
                    )
                    if gasto.cantidad_areas != 0
                    else gasto.cantidad * dias_semana.get(gasto.dia_semana, 0),
                }
            )
        elif gasto.frecuencia == FrecuenciaChoices.LUNES_SABADO:
            gastos_fijos.append(
                {
                    "descripcion": gasto.descripcion,
                    "cantidad": (
                        gasto.cantidad * dias_laborables / gasto.cantidad_areas
                    )
                    if gasto.cantidad_areas != 0
                    else gasto.cantidad * dias_laborables,
                }
            )
        elif gasto.frecuencia == FrecuenciaChoices.DIARIO:
            dias_transcurridos = (parse_hasta - parse_desde).days + 1
            gastos_fijos.append(
                {
                    "descripcion": gasto.descripcion,
                    "cantidad": (
                        gasto.cantidad * dias_transcurridos / gasto.cantidad_areas
                    )
                    if gasto.cantidad_areas != 0
                    else gasto.cantidad * dias_transcurridos,
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

    ventas_para_subtotales = Ventas.objects.filter(**filtros_ventas)

    subtotal_transferencia = (
        Transacciones.objects.filter(
            venta__in=ventas_para_subtotales,
            tipo__in=[TipoTranferenciaChoices.VENTA, TipoTranferenciaChoices.INGRESO],
            cuenta__tipo=CuentasChoices.BANCARIA,
        ).aggregate(transferencia=Sum("cantidad"))["transferencia"]
        or 0
    )

    subtotal_efectivo_bruto = (
        Transacciones.objects.filter(
            venta__in=ventas_para_subtotales,
            tipo__in=[TipoTranferenciaChoices.VENTA, TipoTranferenciaChoices.INGRESO],
            cuenta__tipo=CuentasChoices.EFECTIVO,
        ).aggregate(efectivo=Sum("cantidad"))["efectivo"]
        or 0
    )

    pago_trabajador = (
        Transacciones.objects.filter(
            venta__in=ventas_para_subtotales,
            tipo__in=[
                TipoTranferenciaChoices.PAGO_TRABAJADOR,
                TipoTranferenciaChoices.EGRESO,
            ],
            cuenta__tipo=CuentasChoices.EFECTIVO,
        ).aggregate(transf=Sum("cantidad"))["transf"]
        or 0
    )

    subtotal = subtotal_efectivo_bruto + subtotal_transferencia
    costo_productos = (
        producto_info.aggregate(costo_productos=Sum("costo"))["costo_productos"] or 0
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
        gastos_variables_queryset_sin_pago_trabajador.aggregate(total=Sum("cantidad"))[
            "total"
        ]
        or 0
    )

    gastos_variables = monto_gastos_variables + pago_trabajador

    # total_gatos = Decimal(total_gastos_fijos) + gastos_variables
    # Esto es hasta que se vuelvan a activar los gastos fijos
    total_gatos = gastos_variables

    total_efectivo = subtotal_efectivo_bruto - total_gatos
    total_transferencia = subtotal_transferencia
    total = total_efectivo + total_transferencia

    ganancia = total - costo_productos

    if area == "general":
        reporte_cafeteria = get_reporte_ventas_cafeteria(parse_desde, parse_hasta)

        productos_cafeteria_parseados = []
        for producto in reporte_cafeteria.get("productos"):
            producto_parseado = {
                "id": producto.get("id"),
                "descripcion": producto.get("nombre"),
                "cantidad": producto.get("cantidad"),
                "importe": producto.get("importe"),
                "precio_venta": producto.get("precio_venta"),
            }
            productos_cafeteria_parseados.append(producto_parseado)

        elaboraciones_cafeteria_parseadas = []
        for elaboracion in reporte_cafeteria.get("elaboraciones"):
            elaboracion_parseada = {
                "id": elaboracion.id,
                "descripcion": elaboracion.nombre,
                "cantidad": elaboracion.cantidad,
                "importe": elaboracion.importe,
                "precio_venta": elaboracion.precio_unitario,
            }
            elaboraciones_cafeteria_parseadas.append(elaboracion_parseada)

        return {
            "productos": productos_sin_repeticion
            + productos_cafeteria_parseados
            + elaboraciones_cafeteria_parseadas,
            "subtotal": {
                "general": subtotal + reporte_cafeteria.get("subtotal").get("general"),
                "efectivo": subtotal_efectivo_bruto
                + reporte_cafeteria.get("subtotal").get("efectivo"),
                "transferencia": subtotal_transferencia
                + reporte_cafeteria.get("subtotal").get("transferencia"),
            },
            "gastos_fijos": gastos_fijos,
            "gastos_variables": list(gastos_variables_queryset_sin_pago_trabajador)
            + list(reporte_cafeteria.get("gastos_variables")),
            "pago_trabajador": round(pago_trabajador, 2),
            "mano_obra": reporte_cafeteria.get("mano_obra"),
            "mano_obra_cuenta_casa": reporte_cafeteria.get("mano_obra_cuenta_casa"),
            "ventas_por_usuario": ventas_por_usuario,
            "total": {
                "general": total
                + reporte_cafeteria.get("subtotal").get("general")
                - reporte_cafeteria.get("mano_obra")
                - reporte_cafeteria.get("mano_obra_cuenta_casa"),
                "efectivo": total_efectivo
                + reporte_cafeteria.get("subtotal").get("efectivo")
                - reporte_cafeteria.get("mano_obra")
                - reporte_cafeteria.get("mano_obra_cuenta_casa"),
                "transferencia": total_transferencia
                + reporte_cafeteria.get("total").get("transferencia"),
            },
            "ganancia": ganancia + reporte_cafeteria.get("ganancia"),
            "area": "general",
        }

    return {
        "productos": productos_sin_repeticion,
        "subtotal": {
            "general": subtotal,
            "efectivo": subtotal_efectivo_bruto,
            "transferencia": subtotal_transferencia,
        },
        "gastos_fijos": gastos_fijos,
        "gastos_variables": gastos_variables_queryset_sin_pago_trabajador,
        "pago_trabajador": round(pago_trabajador, 2),
        "ventas_por_usuario": ventas_por_usuario,
        "total": {
            "general": total,
            "efectivo": total_efectivo,
            "transferencia": total_transferencia,
        },
        "ganancia": ganancia,
        "area": area_venta.nombre,
    }
