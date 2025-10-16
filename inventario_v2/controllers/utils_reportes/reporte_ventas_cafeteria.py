from datetime import date
from decimal import Decimal

from django.db.models.functions import Coalesce
from inventario_v2.utils import (
    calcular_dias_laborables,
    obtener_dias_semana_rango,
    obtener_ultimo_dia_mes,
)
from inventario.models import (
    HistorialPrecioCostoCafeteria,
    HistorialPrecioVentaCafeteria,
    PrecioElaboracion,
    Elaboraciones,
    Ventas_Cafeteria,
    Transacciones,
    TipoTranferenciaChoices,
    CuentasChoices,
    Gastos,
    GastosChoices,
    FrecuenciaChoices,
    CuentaCasa,
    Productos_Cafeteria,
)
from django.db.models import (
    OuterRef,
    Subquery,
    F,
    Sum,
    Case,
    When,
    IntegerField,
)


def get_reporte_ventas_cafeteria(desde: date, hasta: date):
    dias_laborables = calcular_dias_laborables(desde, hasta)
    ultimo_dia_hasta = obtener_ultimo_dia_mes(hasta)
    dias_semana = obtener_dias_semana_rango(desde, hasta)

    historico_costo = (
        HistorialPrecioCostoCafeteria.objects.filter(
            producto=OuterRef("pk"),
            fecha_inicio__lte=OuterRef(
                "productos_ventas_cafeteria__ventas_cafeteria__created_at"
            ),
        )
        .order_by("-fecha_inicio")
        .values("precio")[:1]
    )

    respaldo_costo = (
        HistorialPrecioCostoCafeteria.objects.filter(
            producto=OuterRef("pk"),
        )
        .order_by("fecha_inicio")
        .values("precio")[:1]
    )

    historico_venta = (
        HistorialPrecioVentaCafeteria.objects.filter(
            producto=OuterRef("pk"),
            fecha_inicio__lte=OuterRef(
                "productos_ventas_cafeteria__ventas_cafeteria__created_at"
            ),
        )
        .order_by("-fecha_inicio")
        .values("precio")[:1]
    )

    respaldo_venta = (
        HistorialPrecioVentaCafeteria.objects.filter(
            producto=OuterRef("pk"),
        )
        .order_by("fecha_inicio")
        .values("precio")[:1]
    )

    productos = (
        Productos_Cafeteria.objects.filter(
            productos_ventas_cafeteria__ventas_cafeteria__created_at__date__range=(
                desde,
                hasta,
            )
        )
        .annotate(
            cantidad=F("productos_ventas_cafeteria__cantidad"),
            precio_c=Coalesce(Subquery(historico_costo), Subquery(respaldo_costo)),
            precio_v=Coalesce(Subquery(historico_venta), Subquery(respaldo_venta)),
            importe=F("cantidad") * F("precio_v"),
            costo=F("cantidad") * F("precio_c"),
        )
        .values(
            "id",
            "nombre",
            "cantidad",
            "importe",
            "costo",
            precio_costo=F("precio_c"),
            precio_venta=F("precio_v"),
        )
    )

    historico_precio_elaboracion = (
        PrecioElaboracion.objects.filter(
            elaboracion=OuterRef("pk"),
            fecha_inicio__lte=OuterRef(
                "elaboraciones_ventas_cafeteria__ventas_cafeteria__created_at"
            ),
        )
        .order_by("-fecha_inicio")
        .values("precio")[:1]
    )

    respaldo_precio_elaboracion = (
        PrecioElaboracion.objects.filter(
            elaboracion=OuterRef("pk"),
        )
        .order_by("fecha_inicio")
        .values("precio")[:1]
    )

    elaboraciones = Elaboraciones.objects.filter(
        elaboraciones_ventas_cafeteria__ventas_cafeteria__created_at__date__range=(
            desde,
            hasta,
        )
    ).annotate(
        cantidad=F("elaboraciones_ventas_cafeteria__cantidad"),
        precio_unitario=Coalesce(
            Subquery(historico_precio_elaboracion),
            Subquery(respaldo_precio_elaboracion),
        ),
        importe=F("cantidad") * F("precio_unitario"),
    )

    ventas_para_subtotales = Ventas_Cafeteria.objects.filter(
        created_at__date__range=(
            desde,
            hasta,
        )
    )

    subtotal_efectivo = (
        Transacciones.objects.filter(
            venta_cafeteria__in=ventas_para_subtotales,
            tipo=TipoTranferenciaChoices.INGRESO,
            cuenta__tipo=CuentasChoices.EFECTIVO,
        ).aggregate(total=Sum("cantidad"))["total"]
        or 0
    )

    subtotal_transferencia = (
        Transacciones.objects.filter(
            venta_cafeteria__in=ventas_para_subtotales,
            tipo=TipoTranferenciaChoices.INGRESO,
            cuenta__tipo=CuentasChoices.BANCARIA,
        ).aggregate(total=Sum("cantidad"))["total"]
        or 0
    )

    costo_productos = (
        productos.aggregate(costo_productos=Sum(F("costo")))["costo_productos"] or 0
    )

    elaboraciones_sin_repeticion = []
    productos_agrupados = {}

    for producto in productos:
        producto_id = producto["id"]
        if producto_id not in productos_agrupados:
            productos_agrupados[producto_id] = {
                "id": producto_id,
                "nombre": producto["nombre"],
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

    mano_obra = 0
    costo_ingredientes_elaboraciones = 0

    for elaboracion in elaboraciones:
        if elaboracion not in elaboraciones_sin_repeticion:
            elaboraciones_sin_repeticion.append(elaboracion)
        else:
            elaboraciones_sin_repeticion[
                elaboraciones_sin_repeticion.index(elaboracion)
            ].cantidad += elaboracion.cantidad
            elaboraciones_sin_repeticion[
                elaboraciones_sin_repeticion.index(elaboracion)
            ].importe += elaboracion.importe

        mano_obra += elaboracion.mano_obra * elaboracion.cantidad

        for ingrediente in elaboracion.ingredientes_cantidad.all():
            costo_ingredientes_elaboraciones += (
                ingrediente.cantidad
                * ingrediente.ingrediente.precio_costo
                * elaboracion.cantidad
            )

    total_costo_producto = costo_productos + costo_ingredientes_elaboraciones

    mano_obra_cuenta_casa = 0
    cuentas_casa = CuentaCasa.objects.filter(
        created_at__date__range=(desde, hasta),
    )

    for cuenta_casa in cuentas_casa:
        for elaboracion in cuenta_casa.elaboraciones.all():
            mano_obra_cuenta_casa += (
                elaboracion.producto.mano_obra * elaboracion.cantidad
            )

    subtotal_productos = (
        productos.aggregate(subtotal=Sum(F("importe")))["subtotal"] or 0
    )
    subtotal_elaboraciones = (
        elaboraciones.aggregate(subtotal=Sum(F("importe")))["subtotal"] or 0
    )
    subtotal = subtotal_productos + subtotal_elaboraciones

    total_productos = productos.aggregate(total=Sum(F("importe")))["total"] or 0
    total_elaboraciones = elaboraciones.aggregate(total=Sum(F("importe")))["total"] or 0
    total = total_productos + total_elaboraciones - mano_obra - mano_obra_cuenta_casa

    ganancia = total - total_costo_producto or 0

    return {
        "productos": productos_sin_repeticion,
        "elaboraciones": elaboraciones_sin_repeticion,
        "total": {
            "general": total,
            "efectivo": subtotal_efectivo - mano_obra - mano_obra_cuenta_casa,
            "transferencia": subtotal_transferencia,
        },
        "subtotal": {
            "general": subtotal,
            "efectivo": subtotal_efectivo,
            "transferencia": subtotal_transferencia,
        },
        "mano_obra": mano_obra,
        "mano_obra_cuenta_casa": mano_obra_cuenta_casa or 0,
        "ganancia": ganancia,
    }
