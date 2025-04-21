from datetime import datetime
from typing import List
from ninja.errors import HttpError
from inventario.models import (
    METODO_PAGO,
    Elaboraciones_Ventas_Cafeteria,
    FrecuenciaChoices,
    Gastos,
    GastosChoices,
    Inventario_Area_Cafeteria,
    Productos_Ventas_Cafeteria,
    User,
    Cuentas,
    Transacciones,
    TipoTranferenciaChoices,
    Elaboraciones,
    Ingrediente_Cantidad,
    Productos_Cafeteria,
    Inventario_Almacen_Cafeteria,
    Ventas_Cafeteria,
    MermaCafeteria,
    CuentaCasa,
    CuentasChoices,
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
    Add_Venta_Cafeteria,
    CafeteriaReporteSchema,
    EndPointCafeteria,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from django.db.models import Q, Sum, Value, F, Case, When, BooleanField, IntegerField
from django.db.models.functions import Coalesce


@api_controller("cafeteria/", tags=["Cafetería"], permissions=[])
class CafeteriaController:
    @route.get("", response=EndPointCafeteria)
    def get_inventario_cafeteria(self):

        inventario = Productos_Cafeteria.objects.filter(inventario_area__cantidad__gt=0)
        ventas = (
            Ventas_Cafeteria.objects.all()
            .annotate(
                importe=Coalesce(
                    Sum(
                        F("productos__producto__precio_venta")
                        * F("productos__cantidad")
                    ),
                    Value(Decimal(0)),
                )
                + Coalesce(
                    Sum(
                        F("elaboraciones__producto__precio")
                        * F("elaboraciones__cantidad")
                    ),
                    Value(Decimal(0)),
                ),
                tarjeta=F("transacciones__cuenta__nombre"),
            )
            .order_by("-id")
            .distinct()
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
            "ventas": ventas,
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

        productos = Productos_Cafeteria.objects.filter(
            productos_ventas_cafeteria__ventas_cafeteria__created_at__date__range=(
                parse_desde,
                parse_hasta,
            )
        ).annotate(
            cantidad=F("productos_ventas_cafeteria__cantidad"),
            importe=F("cantidad") * F("precio_venta"),
        )

        elaboraciones = Elaboraciones.objects.filter(
            elaboraciones_ventas_cafeteria__ventas_cafeteria__created_at__date__range=(
                parse_desde,
                parse_hasta,
            )
        ).annotate(
            cantidad=F("elaboraciones_ventas_cafeteria__cantidad"),
            importe=F("cantidad") * F("precio"),
        )

        efectivo_productos = (
            productos.aggregate(
                efectivo=Sum(
                    F("importe"),
                    filter=Q(
                        productos_ventas_cafeteria__ventas_cafeteria__metodo_pago=METODO_PAGO.EFECTIVO
                    ),
                ),
            )["efectivo"]
            or 0
        )

        transferencia_productos = (
            productos.aggregate(
                transferencia=Sum(
                    F("importe"),
                    filter=Q(
                        productos_ventas_cafeteria__ventas_cafeteria__metodo_pago=METODO_PAGO.TRANSFERENCIA
                    ),
                ),
            )["transferencia"]
            or 0
        )

        efectivo_elaboraciones = (
            elaboraciones.aggregate(
                efectivo=Sum(
                    F("importe"),
                    filter=Q(
                        elaboraciones_ventas_cafeteria__ventas_cafeteria__metodo_pago=METODO_PAGO.EFECTIVO
                    ),
                ),
            )["efectivo"]
            or 0
        )

        transferencia_elaboraciones = (
            elaboraciones.aggregate(
                transferencia=Sum(
                    F("importe"),
                    filter=Q(
                        elaboraciones_ventas_cafeteria__ventas_cafeteria__metodo_pago=METODO_PAGO.TRANSFERENCIA
                    ),
                ),
            )["transferencia"]
            or 0
        )

        efectivo_y_transferencia_ventas = Ventas_Cafeteria.objects.filter(
            created_at__date__range=(
                parse_desde,
                parse_hasta,
            )
        ).aggregate(efectivo=Sum(F("efectivo")), transferencia=Sum(F("transferencia")))

        efectivo = (
            efectivo_productos
            + efectivo_elaboraciones
            + (efectivo_y_transferencia_ventas["efectivo"] or 0)
        )
        transferencia = (
            transferencia_productos
            + transferencia_elaboraciones
            + (efectivo_y_transferencia_ventas["transferencia"] or 0)
        )

        costo_producto = (
            productos.aggregate(costo_producto=Sum(F("cantidad") * F("precio_costo")))[
                "costo_producto"
            ]
            or 0
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

        gastos_fijos = Gastos.objects.filter(
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

        gastos_fijos_mensuales = (
            gastos_fijos.filter(
                frecuencia=FrecuenciaChoices.MENSUAL,
                dia_mes_ajustado__range=(parse_desde.day, parse_hasta.day + 1),
            ).aggregate(total=Sum("cantidad"))["total"]
            or 0
        )

        gastos_fijos_semanales = gastos_fijos.filter(
            frecuencia=FrecuenciaChoices.SEMANAL,
            dia_semana__in=dias_semana,
        )

        total_gastos_fijos_semanales = sum(
            gasto.cantidad * dias_semana.get(gasto.dia_semana, 0)
            for gasto in gastos_fijos_semanales
        )

        gastos_lunes_sabado = (
            gastos_fijos.filter(frecuencia=FrecuenciaChoices.LUNES_SABADO).aggregate(
                total=Sum("cantidad")
            )["total"]
            or 0
        )

        total_gastos_lunes_sabado = gastos_lunes_sabado * dias_laborables

        total_gastos_fijos = (
            gastos_fijos_mensuales
            + total_gastos_fijos_semanales
            + total_gastos_lunes_sabado
        )

        # Recorrer productos y elaboraciones para evitar repeticiones
        productos_sin_repeticion = []
        elaboraciones_sin_repeticion = []
        for producto in productos:
            if producto not in productos_sin_repeticion:
                productos_sin_repeticion.append(producto)
            else:
                productos_sin_repeticion[
                    productos_sin_repeticion.index(producto)
                ].cantidad += producto.cantidad
                productos_sin_repeticion[
                    productos_sin_repeticion.index(producto)
                ].importe += producto.importe

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

        total_costo_producto = costo_producto + costo_ingredientes_elaboraciones

        total_merma = 0
        mermas = MermaCafeteria.objects.filter(
            created_at__date__range=(parse_desde, parse_hasta),
        )

        for merma in mermas:
            for producto in merma.productos.all():
                total_merma += producto.producto.precio_costo * producto.cantidad

            for elaboracion in merma.elaboraciones.all():
                for ingrediente in elaboracion.producto.ingredientes_cantidad.all():
                    total_merma += (
                        ingrediente.ingrediente.precio_costo * ingrediente.cantidad
                    )

        total_cuenta_casa = 0
        cuentas_casa = CuentaCasa.objects.filter(
            created_at__date__range=(parse_desde, parse_hasta),
        )

        for cuenta_casa in cuentas_casa:
            for producto in cuenta_casa.productos.all():
                total_cuenta_casa += producto.producto.precio_costo * producto.cantidad

            for elaboracion in cuenta_casa.elaboraciones.all():
                for ingrediente in elaboracion.producto.ingredientes_cantidad.all():
                    total_cuenta_casa += (
                        ingrediente.ingrediente.precio_costo * ingrediente.cantidad
                    )
                total_cuenta_casa += elaboracion.producto.mano_obra

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
            - total_gastos_fijos
            - monto_gastos_variables
            # - total_merma
            # - total_cuenta_casa
        )

        return {
            "productos": productos_sin_repeticion,
            "elaboraciones": elaboraciones_sin_repeticion,
            "total": {
                "general": total,
                "efectivo": efectivo
                - mano_obra
                - total_gastos_fijos
                - monto_gastos_variables,
                "transferencia": transferencia,
            },
            "subtotal": {
                "general": subtotal,
                "efectivo": efectivo,
                "transferencia": transferencia,
            },
            "merma": total_merma,
            "cuenta_casa": total_cuenta_casa,
            "mano_obra": mano_obra,
            "gastos_variables": gastos_variables,
            "gastos_fijos": total_gastos_fijos,
        }

    @route.post("productos/")
    def add_productos_cafeteria(self, request, body: Add_Producto_Cafeteria):
        body_dict = body.model_dump()

        producto = Productos_Cafeteria.objects.create(**body_dict)
        Inventario_Almacen_Cafeteria.objects.create(producto=producto, cantidad=0)
        Inventario_Area_Cafeteria.objects.create(producto=producto, cantidad=0)
        return

    @route.post("elaboraciones/")
    def add_elaboracion(self, request, body: Add_Elaboracion):
        body_dict = body.model_dump()

        with transaction.atomic():
            elaboracion = Elaboraciones.objects.create(
                nombre=body_dict["nombre"],
                precio=body_dict["precio"],
                mano_obra=body_dict["mano_obra"],
            )

            for ingrediente in body_dict["ingredientes"]:
                producto = get_object_or_404(
                    Productos_Cafeteria, pk=ingrediente["producto"]
                )
                ingrediente = Ingrediente_Cantidad.objects.create(
                    ingrediente=producto, cantidad=ingrediente["cantidad"]
                )
                elaboracion.ingredientes_cantidad.add(ingrediente)

        return

    @route.post("ventas/")
    def add_venta(self, request, body: Add_Venta_Cafeteria):
        body_dict = body.model_dump()

        usuario = get_object_or_404(User, id=request.auth["id"])

        with transaction.atomic():
            venta = Ventas_Cafeteria.objects.create(
                usuario=usuario,
                metodo_pago=body.metodo_pago,
                efectivo=body.efectivo,
                transferencia=body.transferencia,
            )

            total_cantidad_productos = 0
            total_cantidad_elaboraciones = 0
            total_venta = Decimal(0)

            for prod_elb in body.productos:
                if prod_elb.isElaboracion:
                    elaboracion = get_object_or_404(Elaboraciones, id=prod_elb.producto)
                    for ingrediente in elaboracion.ingredientes_cantidad.all():
                        inventario = get_object_or_404(
                            Inventario_Area_Cafeteria,
                            producto__id=ingrediente.ingrediente.pk,
                        )

                        if inventario.cantidad < ingrediente.cantidad * Decimal(
                            prod_elb.cantidad
                        ):
                            raise HttpError(
                                400,
                                f"No hay suficiente {ingrediente.ingrediente.nombre}.",
                            )

                        inventario.cantidad -= ingrediente.cantidad * Decimal(
                            prod_elb.cantidad
                        )
                        inventario.save()

                    total_cantidad_elaboraciones += Decimal(prod_elb.cantidad)
                    total_venta += elaboracion.precio * Decimal(prod_elb.cantidad)

                    elaboraciones_ventas_cafeteria = (
                        Elaboraciones_Ventas_Cafeteria.objects.create(
                            producto=elaboracion,
                            cantidad=prod_elb.cantidad,
                        )
                    )
                    venta.elaboraciones.add(elaboraciones_ventas_cafeteria)
                else:
                    producto = get_object_or_404(
                        Productos_Cafeteria, id=prod_elb.producto
                    )
                    inventario = get_object_or_404(
                        Inventario_Area_Cafeteria, producto=producto
                    )
                    if inventario.cantidad < Decimal(prod_elb.cantidad):
                        raise HttpError(
                            400, f"No hay suficiente {producto.nombre} en inventario."
                        )
                    inventario.cantidad -= Decimal(prod_elb.cantidad)
                    inventario.save()

                    total_cantidad_productos += Decimal(prod_elb.cantidad)
                    total_venta += producto.precio_venta * Decimal(prod_elb.cantidad)

                    productos_ventas_cafeteria = (
                        Productos_Ventas_Cafeteria.objects.create(
                            producto=producto,
                            cantidad=Decimal(prod_elb.cantidad),
                        )
                    )
                    venta.productos.add(productos_ventas_cafeteria)

            if body.metodo_pago == METODO_PAGO.MIXTO and total_venta != Decimal(
                body_dict["efectivo"]
            ) + Decimal(body_dict["transferencia"]):
                raise HttpError(
                    400,
                    "El importe no coincide con la suma de efectivo y transferencia",
                )

            if body.metodo_pago != METODO_PAGO.EFECTIVO:
                cuenta_transaferencia = get_object_or_404(Cuentas, id=body.tarjeta)
            cuenta_efectivo = get_object_or_404(Cuentas, id=25)

            if body.metodo_pago == METODO_PAGO.MIXTO:
                descripcion = (
                    f"[MIXTO] {total_cantidad_productos}x Prod"
                    f", {total_cantidad_elaboraciones}x Elab"
                    " - Cafetería"
                )
            else:
                descripcion = (
                    f"{total_cantidad_productos}x Prod"
                    f", {total_cantidad_elaboraciones}x Elab"
                    " - Cafetería"
                )

            if body.metodo_pago == METODO_PAGO.MIXTO:
                transferencia = Decimal(body_dict["transferencia"])
                efectivo = Decimal(body_dict["efectivo"])

            if body.metodo_pago == METODO_PAGO.MIXTO:
                Transacciones.objects.create(
                    cuenta=cuenta_transaferencia,
                    cantidad=transferencia,
                    descripcion=descripcion,
                    tipo=TipoTranferenciaChoices.INGRESO,
                    usuario=usuario,
                    venta_cafeteria=venta,
                )
                cuenta_transaferencia.saldo += transferencia
                cuenta_transaferencia.save()
                Transacciones.objects.create(
                    cuenta=cuenta_efectivo,
                    cantidad=efectivo,
                    descripcion=descripcion,
                    tipo=TipoTranferenciaChoices.INGRESO,
                    usuario=usuario,
                    venta_cafeteria=venta,
                )
                cuenta_efectivo.saldo += transferencia
                cuenta_efectivo.save()

            elif body.metodo_pago == METODO_PAGO.TRANSFERENCIA:
                Transacciones.objects.create(
                    cuenta=cuenta_transaferencia,
                    cantidad=total_venta,
                    descripcion=descripcion,
                    tipo=TipoTranferenciaChoices.INGRESO,
                    usuario=usuario,
                    venta_cafeteria=venta,
                )
                cuenta_transaferencia.saldo += total_venta
                cuenta_transaferencia.save()

            else:
                Transacciones.objects.create(
                    cuenta=cuenta_efectivo,
                    cantidad=total_venta,
                    descripcion=descripcion,
                    tipo=TipoTranferenciaChoices.INGRESO,
                    usuario=usuario,
                    venta_cafeteria=venta,
                )
                cuenta_efectivo.saldo += total_venta
                cuenta_efectivo.save()

        return

    @route.put("productos/{id}/")
    def edit_productos_cafeteria(self, id: int, body: Add_Producto_Cafeteria):
        body_dict = body.model_dump()

        producto = get_object_or_404(Productos_Cafeteria, id=id)
        producto.nombre = body_dict["nombre"]
        producto.precio_costo = body_dict["precio_costo"]
        producto.precio_venta = body_dict["precio_venta"]
        producto.save()

        return

    @route.put("elaboraciones/{id}/")
    def edit_elaboracion(self, id: int, body: Add_Elaboracion):
        body_dict = body.model_dump()

        with transaction.atomic():
            elaboracion = get_object_or_404(Elaboraciones, id=id)
            elaboracion.nombre = body_dict["nombre"]
            elaboracion.precio = body_dict["precio"]
            elaboracion.mano_obra = body_dict["mano_obra"]

            # { id_ingrediente : <Ingrediente_Cantidad> }
            ingredientes_existentes_dict = {
                ingrediente.ingrediente.id: ingrediente
                for ingrediente in elaboracion.ingredientes_cantidad.all()
            }

            # Agregar o actualizar
            for ingrediente_nuevo in body_dict["ingredientes"]:
                if ingrediente_nuevo["producto"] in ingredientes_existentes_dict:
                    # Actualizar la cantidad
                    ingrediente_existente = ingredientes_existentes_dict[
                        ingrediente_nuevo["producto"]
                    ]
                    ingrediente_existente.cantidad = ingrediente_nuevo["cantidad"]
                    ingrediente_existente.save()
                else:
                    # Agregar
                    producto = get_object_or_404(
                        Productos_Cafeteria, pk=ingrediente_nuevo["producto"]
                    )
                    ingrediente = Ingrediente_Cantidad.objects.create(
                        ingrediente=producto, cantidad=ingrediente_nuevo["cantidad"]
                    )
                    elaboracion.ingredientes_cantidad.add(ingrediente)

            # Eliminar ingredientes que no están en la lista de nuevos ingredientes
            for ingrediente_existente_id in list(ingredientes_existentes_dict.keys()):
                if ingrediente_existente_id not in [
                    ingrediente["producto"] for ingrediente in body_dict["ingredientes"]
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

    @route.delete("ventas/{id}/")
    def delete_ventas_cafeteria(self, id: int):
        with transaction.atomic():
            venta = get_object_or_404(Ventas_Cafeteria, id=id)

            for producto_venta_cafeteria in venta.productos.all():
                inventario = get_object_or_404(
                    Inventario_Area_Cafeteria,
                    producto=producto_venta_cafeteria.producto,
                )
                inventario.cantidad += producto_venta_cafeteria.cantidad
                inventario.save()

            for elaboracion_venta_cafeteria in venta.elaboraciones.all():
                for (
                    ingrediente_cantidad
                ) in elaboracion_venta_cafeteria.producto.ingredientes_cantidad.all():
                    inventario = get_object_or_404(
                        Inventario_Area_Cafeteria,
                        producto=ingrediente_cantidad.ingrediente,
                    )
                    inventario.cantidad += ingrediente_cantidad.cantidad * Decimal(
                        elaboracion_venta_cafeteria.cantidad
                    )
                    inventario.save()

            transacciones = Transacciones.objects.filter(venta_cafeteria=venta)
            for transaccion in transacciones:
                cuenta = Cuentas.objects.get(pk=transaccion.cuenta.pk)
                cuenta.saldo -= transaccion.cantidad
                cuenta.save()

            transaccion.delete()

            venta.delete()
