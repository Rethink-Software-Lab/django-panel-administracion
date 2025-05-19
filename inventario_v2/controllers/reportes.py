from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from django.shortcuts import get_object_or_404
from inventario.models import (
    ProductoInfo,
    Ventas,
    AreaVenta,
    Gastos,
    GastosChoices,
    FrecuenciaChoices,
    Productos_Cafeteria,
    HistorialPrecioCostoSalon,
    HistorialPrecioVentaSalon,
    Producto,
)
from ..schema import ReportesSchema
from ninja_extra import api_controller, route
from django.db.models import (
    F,
    Count,
    Q,
    Sum,
    When,
    Case,
    IntegerField,
    ExpressionWrapper,
    DecimalField,
)
from ..utils import (
    calcular_dias_laborables,
    obtener_dias_semana_rango,
    obtener_ultimo_dia_mes,
)
from django.db.models.functions import Coalesce
from django.db.models import OuterRef, Subquery


@api_controller("reportes/", tags=["Categorías"], permissions=[])
class ReportesController:
    @route.get("", response=ReportesSchema)
    def getReportes(
        self,
        type: Literal["ventas", "inventario"] = "ventas",
        area: str = "general",
        desde: datetime = datetime.today(),
        hasta: datetime = datetime.today(),
        categoria: str = "todas",
    ):
        parse_desde = desde.date()
        parse_hasta = hasta.date()

        dias_laborables = calcular_dias_laborables(parse_desde, parse_hasta)
        ultimo_dia_hasta = obtener_ultimo_dia_mes(parse_hasta)
        dias_semana = obtener_dias_semana_rango(parse_desde, parse_hasta)

        if type == "ventas":
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

            gastos_fijos_result = Gastos.objects.filter(
                **filtros_gastos_fijos
            ).annotate(
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
                    and gasto.dia_mes_ajustado
                    in range(parse_desde.day, parse_hasta.day + 1)
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
                            "cantidad": gasto.cantidad
                            * dias_semana.get(gasto.dia_semana, 0),
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

            historico_venta = (
                HistorialPrecioVentaSalon.objects.filter(
                    producto_info=OuterRef("pk"),
                    fecha_inicio__lte=OuterRef("producto__venta__created_at"),
                )
                .order_by("-fecha_inicio")
                .values("precio")[:1]
            )

            productos_info_qs = productos_info_qs.annotate(
                precio_c=Subquery(historico_costo),
                precio_v=Subquery(historico_venta),
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
                # .annotate(importe=F("importe") - F("costo_total"))
                .values(
                    "id",
                    "importe",
                    "cantidad",
                    "descripcion",
                    precio_venta=F("precio_v"),
                    precio_costo=F("precio_c"),
                )
                .distinct()
                .order_by("-importe")
            )

            filtros_ventas: dict[str, str | tuple[date, date]] = {
                "created_at__date__range": (parse_desde, parse_hasta)
            }

            if area != "general":
                filtros_ventas["area_venta__id"] = area

            ventas = Ventas.objects.filter(**filtros_ventas)

            if area != "general":
                area_venta = get_object_or_404(AreaVenta, pk=area)

            total_gastos_fijos = sum(gasto.get("cantidad", 0) for gasto in gastos_fijos)

            pagos = ventas.aggregate(
                efectivo=Coalesce(
                    Sum(
                        "producto__info__historial_venta__precio",
                        filter=Q(metodo_pago="EFECTIVO"),
                    ),
                    Decimal(0),
                )
                + Coalesce(
                    Sum(
                        "efectivo",
                        filter=Q(metodo_pago="MIXTO"),
                    ),
                    Decimal(0),
                ),
                transferencia=Coalesce(
                    Sum(
                        "producto__info__historial_venta__precio",
                        filter=Q(metodo_pago="TRANSFERENCIA"),
                    ),
                    Decimal(0),
                )
                + Coalesce(
                    Sum(
                        "transferencia",
                        filter=Q(metodo_pago="MIXTO"),
                    ),
                    Decimal(0),
                ),
            )

            efectivo = pagos.get("efectivo", Decimal(0))
            transferencia = pagos.get("transferencia", Decimal(0))

            subtotal = producto_info.aggregate(subtotal=Sum("importe"))["subtotal"] or 0

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
                usuario = producto.get("usuario", "Sin usuario")

                if usuario not in ventas_por_usuario:
                    ventas_por_usuario[usuario] = 0

                ventas_por_usuario[usuario] += producto.get("pago", 0)

            monto_gastos_variables = (
                gastos_variables.aggregate(total=Sum("cantidad"))["total"] or 0
            ) + pago_trabajador

            total_costos = total_gastos_fijos + monto_gastos_variables or 0

            total = subtotal - total_costos

            return {
                "productos": list(producto_info),
                "subtotal": {
                    "general": subtotal,
                    "efectivo": efectivo,
                    "transferencia": transferencia,
                },
                "gastos_fijos": gastos_fijos,
                "gastos_variables": gastos_variables,
                "pago_trabajador": round(pago_trabajador, 2),
                "ventas_por_usuario": ventas_por_usuario,
                "total": {
                    "general": total,
                    "efectivo": efectivo - total_costos,
                    "transferencia": transferencia,
                },
                "area": area_venta.nombre if area != "general" else "general",
            }

        elif type == "inventario":
            if area == "general":
                area_venta = "General"
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__venta__isnull=True,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(cantidad=Count(F("producto")))
                    .exclude(cantidad__lt=1)
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                    )
                )
                if categoria != "todas":
                    producto_info = producto_info.filter(categoria__id=categoria)

            elif area == "cafeteria":
                area_venta = "Cafetería"
                productos = Productos_Cafeteria.objects.filter(
                    inventario_area__cantidad__gt=0
                )
                producto_info = []
                for producto in productos:
                    producto_info.append(
                        {
                            "id": producto.pk,
                            "descripcion": producto.nombre,
                            "cantidad": producto.inventario_area.cantidad,
                        }
                    )

            elif area == "almacen-cafeteria":
                area_venta = "Almacén Cafetería"
                productos = Productos_Cafeteria.objects.filter(
                    inventario_almacen__cantidad__gt=0
                )
                producto_info = []
                for producto in productos:
                    producto_info.append(
                        {
                            "id": producto.pk,
                            "descripcion": producto.nombre,
                            "cantidad": producto.inventario_almacen.cantidad,
                        }
                    )

            elif area == "almacen-principal":
                area_venta = "Almacén Principal"
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__area_venta__isnull=True,
                        producto__almacen_revoltosa=False,
                        producto__venta__isnull=True,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(cantidad=Count(F("producto")))
                    .exclude(cantidad__lt=1)
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                    )
                )
                if categoria != "todas":
                    producto_info = producto_info.filter(categoria__id=categoria)

            elif area == "almacen-revoltosa":
                area_venta = "Almacén Revoltosa"
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__area_venta__isnull=True,
                        producto__almacen_revoltosa=True,
                        producto__venta__isnull=True,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(cantidad=Count(F("producto")))
                    .exclude(cantidad__lt=1)
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                    )
                )
                if categoria != "todas":
                    producto_info = producto_info.filter(categoria__id=categoria)

            else:
                area_venta = get_object_or_404(AreaVenta, pk=area).nombre
                producto_info = (
                    ProductoInfo.objects.filter(
                        producto__area_venta=area,
                        producto__almacen_revoltosa=False,
                        producto__venta__isnull=True,
                        producto__ajusteinventario__isnull=True,
                    )
                    .annotate(cantidad=Count(F("producto")))
                    .exclude(cantidad__lt=1)
                    .values(
                        "id",
                        "descripcion",
                        "cantidad",
                    )
                )
                if categoria != "todas":
                    producto_info = producto_info.filter(categoria__id=categoria)

            return {"productos": producto_info, "area": area_venta}
