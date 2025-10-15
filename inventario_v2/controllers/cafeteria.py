from datetime import datetime, timedelta
from django.utils import timezone
from typing import List
from inventario.models import (
    METODO_PAGO,
    FrecuenciaChoices,
    Gastos,
    GastosChoices,
    Inventario_Area_Cafeteria,
    User,
    Cuentas,
    Transacciones,
    TipoTranferenciaChoices,
    Elaboraciones,
    Ingrediente_Cantidad,
    Productos_Cafeteria,
    Inventario_Almacen_Cafeteria,
    Ventas_Cafeteria,
    PrecioElaboracion,
    CuentaCasa,
    CuentasChoices,
    HistorialPrecioCostoCafeteria,
    HistorialPrecioVentaCafeteria,
)
from inventario_v2.utils import (
    calcular_dias_laborables,
    obtener_dias_semana_rango,
    obtener_ultimo_dia_mes,
)
from ..schema import (
    ElaboracionesEndpoint,
    Add_Elaboracion,
    Producto_Cafeteria_Endpoint_Schema,
    Add_Producto_Cafeteria,
    Edit_Producto_Cafeteria,
    CafeteriaReporteSchema,
    EndPointCafeteria,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from django.db.models import (
    Q,
    Sum,
    Value,
    F,
    Case,
    When,
    BooleanField,
    IntegerField,
    OuterRef,
    Subquery,
)
from django.db.models.functions import Coalesce


@api_controller("cafeteria/", tags=["Cafetería"], permissions=[])
class CafeteriaController:
    @route.get("", response=EndPointCafeteria)
    def get_inventario_cafeteria(self):
        inventario = Productos_Cafeteria.objects.filter(inventario_area__cantidad__gt=0)

        historico_venta = (
            HistorialPrecioVentaCafeteria.objects.filter(
                producto=OuterRef("producto__id"),
                fecha_inicio__lte=OuterRef("ventas_cafeteria__created_at"),
            )
            .order_by("-fecha_inicio")
            .values("precio")[:1]
        )

        respaldo_venta = (
            HistorialPrecioVentaCafeteria.objects.filter(
                producto=OuterRef("producto__id"),
            )
            .order_by("fecha_inicio")
            .values("precio")[:1]
        )

        historico_precio_elaboracion = (
            PrecioElaboracion.objects.filter(
                elaboracion=OuterRef("producto_id"),
                fecha_inicio__lte=OuterRef("ventas_cafeteria__created_at"),
            )
            .order_by("-fecha_inicio")
            .values("precio")[:1]
        )

        respaldo_precio_elaboracion = (
            PrecioElaboracion.objects.filter(
                elaboracion=OuterRef("producto_id"),
            )
            .order_by("fecha_inicio")
            .values("precio")[:1]
        )

        ventas = (
            Ventas_Cafeteria.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30),
            )
            .annotate(
                cuenta=F("transacciones__cuenta__nombre"),
            )
            .order_by("-id")
            .distinct("id")
        )

        ventas_formated = []

        for venta in ventas:
            if venta.productos:
                productos_venta = venta.productos.all().annotate(
                    importe=F("cantidad")
                    * Coalesce(Subquery(historico_venta), Subquery(respaldo_venta))
                )

            if venta.elaboraciones:
                elaboraciones_venta = venta.elaboraciones.all().annotate(
                    importe=F("cantidad")
                    * Coalesce(
                        Subquery(historico_precio_elaboracion),
                        Subquery(respaldo_precio_elaboracion),
                    )
                )

            importe_total = (
                productos_venta.aggregate(importe_total=Sum(F("importe")))[
                    "importe_total"
                ]
                or 0
                + elaboraciones_venta.aggregate(importe_total=Sum(F("importe")))[
                    "importe_total"
                ]
                or 0
            ) or 0

            ventas_formated.append(
                {
                    "id": venta.pk,
                    "usuario": venta.usuario.username,
                    "productos": productos_venta,
                    "elaboraciones": elaboraciones_venta,
                    "importe": importe_total,
                    "cuenta": venta.cuenta,
                    "efectivo": venta.efectivo,
                    "transferencia": venta.transferencia,
                    "metodo_pago": venta.metodo_pago,
                    "created_at": venta.created_at,
                }
            )

        productos = Productos_Cafeteria.objects.all()

        elaboraciones = Elaboraciones.objects.all()
        tarjetas = Cuentas.objects.filter(tipo=CuentasChoices.BANCARIA).annotate(
            total_ingresos=Sum(
                "transacciones__cantidad",
                filter=Q(
                    transacciones__created_at__month=datetime.now().month,
                    transacciones__tipo=TipoTranferenciaChoices.INGRESO,
                ),
            ),
            disponible=Case(
                When(Q(total_ingresos__gte=Decimal(120000)), then=Value(False)),
                default=Value(True),
                output_field=BooleanField(),
            ),
        )

        productos_elaboraciones = []
        for elaboracion in elaboraciones:
            productos_elaboraciones.append(
                {
                    "id": elaboracion.pk,
                    "nombre": elaboracion.nombre,
                    "isElaboracion": True,
                }
            )
        for producto in productos:
            productos_elaboraciones.append(
                {"id": producto.pk, "nombre": producto.nombre, "isElaboracion": False}
            )

        return {
            "inventario": inventario,
            "ventas": ventas_formated,
            "tarjetas": tarjetas,
            "productos_elaboraciones": productos_elaboraciones,
        }

    @route.get("productos/", response=List[Producto_Cafeteria_Endpoint_Schema])
    def get_productos_cafeteria(self):
        productos = Productos_Cafeteria.objects.all().order_by("-id")

        return productos

    @route.get("elaboraciones/", response=ElaboracionesEndpoint)
    def get_all_elaboraciones(self):
        elaboraciones = Elaboraciones.objects.all().order_by("-id")

        productos = Productos_Cafeteria.objects.all()

        return {"elaboraciones": elaboraciones, "productos": productos}

    @route.get("reportes/", response=CafeteriaReporteSchema)
    def get_reporte(
        self,
        desde: datetime = datetime.today(),
        hasta: datetime = datetime.today(),
    ):
        parse_desde = desde.date()
        parse_hasta = hasta.date()

        dias_laborables = calcular_dias_laborables(parse_desde, parse_hasta)
        ultimo_dia_hasta = obtener_ultimo_dia_mes(parse_hasta)
        dias_semana = obtener_dias_semana_rango(parse_desde, parse_hasta)

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
                    parse_desde,
                    parse_hasta,
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
                parse_desde,
                parse_hasta,
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
                parse_desde,
                parse_hasta,
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

        """ pago_trabajador_para_subtotal_efectivo = (
            Transacciones.objects.filter(
                venta_cafeteria__in=ventas_para_subtotales,
                tipo=TipoTranferenciaChoices.INGRESO,
                cuenta__tipo=CuentasChoices.EFECTIVO,
            ).aggregate(
                pago=Sum("venta_cafeteria__elaboraciones__producto__mano_obra")
            )["pago"]
            or 0
        ) """

        """ transferencia_pago_trabajador = (
            Transacciones.objects.filter(
                venta_cafeteria__in=ventas_para_subtotales,
                tipo=TipoTranferenciaChoices.EGRESO,
                cuenta__tipo=CuentasChoices.EFECTIVO,
            ).aggregate(transf=Sum("cantidad"))["transf"]
            or 0
        ) """

        """ subtotal_efectivo_bruto = (
            subtotal_efectivo + pago_trabajador_para_subtotal_efectivo
        )
        print(pago_trabajador_para_subtotal_efectivo) """
        """ subtotal_efectivo_neto = subtotal_efectivo - transferencia_pago_trabajador """

        costo_productos = (
            productos.aggregate(costo_productos=Sum(F("costo")))["costo_productos"] or 0
        )

        gastos_variables = Gastos.objects.filter(
            tipo=GastosChoices.VARIABLE,
            created_at__date__range=(parse_desde, parse_hasta),
            area_venta=None,
            is_cafeteria=True,
        )

        monto_gastos_variables = (
            gastos_variables.aggregate(total=Sum("cantidad"))["total"] or 0
        )

        gastos_fijos_result = Gastos.objects.filter(
            tipo=GastosChoices.FIJO,
            created_at__date__lte=parse_hasta,
            area_venta=None,
            is_cafeteria=True,
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
                    {"descripcion": gasto.descripcion, "cantidad": gasto.cantidad}
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

        total_gastos_fijos = sum(gasto.get("cantidad", 0) for gasto in gastos_fijos)

        elaboraciones_sin_repeticion = []
        # Recorrer productos y elaboraciones para evitar repeticiones
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
            created_at__date__range=(parse_desde, parse_hasta),
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
        total_elaboraciones = (
            elaboraciones.aggregate(total=Sum(F("importe")))["total"] or 0
        )
        total = (
            total_productos
            + total_elaboraciones
            - mano_obra
            - mano_obra_cuenta_casa
            - total_gastos_fijos
            - monto_gastos_variables
        )

        ganancia = total - total_costo_producto or 0

        print(monto_gastos_variables)

        return {
            "productos": productos_sin_repeticion,
            "elaboraciones": elaboraciones_sin_repeticion,
            "total": {
                "general": total,
                "efectivo": subtotal_efectivo
                - mano_obra
                - mano_obra_cuenta_casa
                - total_gastos_fijos
                - monto_gastos_variables,
                "transferencia": subtotal_transferencia,
            },
            "subtotal": {
                "general": subtotal,
                "efectivo": subtotal_efectivo,
                "transferencia": subtotal_transferencia,
            },
            "mano_obra": mano_obra + mano_obra_cuenta_casa,
            "gastos_variables": gastos_variables,
            "gastos_fijos": gastos_fijos,
            "ganancia": ganancia,
        }

    @route.post("productos/")
    def add_productos_cafeteria(self, request, body: Add_Producto_Cafeteria):
        usuario = get_object_or_404(User, id=request.auth["id"])

        producto = Productos_Cafeteria.objects.create(nombre=body.nombre)
        HistorialPrecioCostoCafeteria.objects.create(
            precio=body.precio_costo, producto=producto, usuario=usuario
        )
        HistorialPrecioVentaCafeteria.objects.create(
            precio=body.precio_venta, producto=producto, usuario=usuario
        )
        Inventario_Almacen_Cafeteria.objects.create(producto=producto, cantidad=0)
        Inventario_Area_Cafeteria.objects.create(producto=producto, cantidad=0)
        return

    @route.post("elaboraciones/")
    def add_elaboracion(self, request, body: Add_Elaboracion):
        usuario = get_object_or_404(User, id=request.auth["id"])

        with transaction.atomic():
            elaboracion = Elaboraciones.objects.create(
                nombre=body.nombre,
                mano_obra=body.mano_obra,
            )

            PrecioElaboracion.objects.create(
                elaboracion=elaboracion, precio=body.precio, usuario=usuario
            )

            for ingrediente in body.ingredientes:
                producto = get_object_or_404(
                    Productos_Cafeteria, pk=ingrediente.producto
                )
                ingrediente = Ingrediente_Cantidad.objects.create(
                    ingrediente=producto, cantidad=ingrediente.cantidad
                )
                elaboracion.ingredientes_cantidad.add(ingrediente)

        return

    @route.put("productos/{id}/")
    def edit_productos_cafeteria(self, request, id: int, body: Edit_Producto_Cafeteria):
        producto = get_object_or_404(Productos_Cafeteria, id=id)
        usuario = get_object_or_404(User, id=request.auth["id"])

        with transaction.atomic():
            if producto.nombre != body.nombre:
                producto.nombre = body.nombre
                producto.save()

            if (
                producto.precio_costo != Decimal(body.precio_costo)
                if body.precio_costo
                else 0
            ):
                HistorialPrecioCostoCafeteria.objects.create(
                    precio=body.precio_costo, usuario=usuario, producto=producto
                )
            if (
                producto.precio_venta != Decimal(body.precio_venta)
                if body.precio_venta
                else 0
            ):
                HistorialPrecioVentaCafeteria.objects.create(
                    precio=body.precio_venta, usuario=usuario, producto=producto
                )

        return

    @route.put("elaboraciones/{id}/")
    def edit_elaboracion(self, request, id: int, body: Add_Elaboracion):
        usuario = get_object_or_404(User, id=request.auth["id"])

        with transaction.atomic():
            elaboracion = get_object_or_404(Elaboraciones, id=id)
            ultimo_precio_elaboracion = PrecioElaboracion.objects.filter(
                elaboracion=elaboracion
            ).first()
            elaboracion.nombre = body.nombre
            elaboracion.mano_obra = Decimal(body.mano_obra)

            if (
                ultimo_precio_elaboracion
                and ultimo_precio_elaboracion.precio != body.precio
            ):
                PrecioElaboracion.objects.create(
                    elaboracion=elaboracion, precio=body.precio, usuario=usuario
                )

            # { id_ingrediente : <Ingrediente_Cantidad> }
            ingredientes_existentes_dict = {
                ingrediente.ingrediente.id: ingrediente
                for ingrediente in elaboracion.ingredientes_cantidad.all()
            }

            # Agregar o actualizar
            for ingrediente_nuevo in body.ingredientes:
                if ingrediente_nuevo.producto in ingredientes_existentes_dict:
                    # Actualizar la cantidad
                    ingrediente_existente = ingredientes_existentes_dict[
                        ingrediente_nuevo.producto
                    ]
                    ingrediente_existente.cantidad = ingrediente_nuevo.cantidad
                    ingrediente_existente.save()
                else:
                    # Agregar
                    producto = get_object_or_404(
                        Productos_Cafeteria, pk=ingrediente_nuevo.producto
                    )
                    ingrediente = Ingrediente_Cantidad.objects.create(
                        ingrediente=producto, cantidad=ingrediente_nuevo.cantidad
                    )
                    elaboracion.ingredientes_cantidad.add(ingrediente)

            # Eliminar ingredientes que no están en la lista de nuevos ingredientes
            for ingrediente_existente_id in list(ingredientes_existentes_dict.keys()):
                if ingrediente_existente_id not in [
                    ingrediente.producto for ingrediente in body.ingredientes
                ]:
                    Ingrediente_Cantidad.objects.filter(
                        ingrediente_id=ingrediente_existente_id
                    ).delete()

            elaboracion.save()

        return

    @route.delete("productos/{id}/")
    def delete_producto_cafeteria(self, id: int):
        producto = get_object_or_404(Productos_Cafeteria, id=id)
        producto.delete()
        return

    @route.delete("elaboraciones/{id}/")
    def delete_elaboracion(self, id: int):
        elaboracion = get_object_or_404(Elaboraciones, id=id)
        for ingredientes_cantidad in elaboracion.ingredientes_cantidad.all():
            ingredientes_cantidad.delete()
        elaboracion.delete()
        return
