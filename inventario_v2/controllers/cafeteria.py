from datetime import datetime
from typing import List
from ninja.errors import HttpError
from inventario.models import (
    METODO_PAGO,
    Elaboraciones_Ventas_Cafeteria,
    FrecuenciaChoices,
    Gastos,
    GastosChoices,
    Productos_Ventas_Cafeteria,
    User,
    Tarjetas,
    BalanceTarjetas,
    TransferenciasTarjetas,
    TipoTranferenciaChoices,
    Elaboraciones,
    ProductoInfo,
    Ingrediente_Cantidad,
    Productos_Cafeteria,
    Inventario_Producto_Cafeteria,
    Entradas_Cafeteria,
    Productos_Entradas_Cafeteria,
    Ventas_Cafeteria,
)
from inventario_v2.utils import (
    calcular_dias_laborables,
    obtener_dias_semana_rango,
    obtener_ultimo_dia_mes,
    validate_transferencia,
)
from ..schema import (
    TarjetasModifySchema,
    TarjetasEndpoint,
    TransferenciasTarjetasModify,
    ElaboracionesSchema,
    ElaboracionesEndpoint,
    Add_Elaboracion,
    Producto_Cafeteria_Schema,
    Entradas_Almacen_Cafeteria_Schema,
    Add_Entrada_Cafeteria,
    Producto_Cafeteria_Endpoint_Schema,
    Add_Producto_Cafeteria,
    Ventas_Cafeteria_Endpoint,
    Add_Venta_Cafeteria,
    CafeteriaReporteSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin, isSupervisor
from django.db import transaction
from decimal import Decimal
from django.db.models import Q, Sum, Value, F, Case, When, BooleanField, IntegerField
from django.db.models.functions import Coalesce, Round


@api_controller("cafeteria/", tags=["Cafetería"], permissions=[isAdmin])
class CafeteriaController:
    @route.get("inventario/", response=List[Producto_Cafeteria_Schema])
    def get_inventario_cafeteria(self):

        productos = Productos_Cafeteria.objects.filter(inventario__cantidad__gt=0)

        return productos

    @route.get("productos/", response=List[Producto_Cafeteria_Endpoint_Schema])
    def get_productos_cafeteria(self):

        productos = Productos_Cafeteria.objects.all().order_by("-id")

        return productos

    @route.get("entradas/", response=Entradas_Almacen_Cafeteria_Schema)
    def get_entradas_cafeteria(self):

        entradas = Entradas_Cafeteria.objects.prefetch_related("productos").order_by(
            "-created_at"
        )
        productos = Productos_Cafeteria.objects.all()

        return {"entradas": entradas, "productos": productos}

    @route.get("ventas/", response=Ventas_Cafeteria_Endpoint)
    def get_ventas_cafeteria(self):
        ventas = (
            Ventas_Cafeteria.objects.all()
            .order_by("-id")
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
                tarjeta=F("transferenciastarjetas__tarjeta__nombre"),
            )
        )

        productos = Productos_Cafeteria.objects.all()
        elaboraciones = Elaboraciones.objects.all()
        tarjetas = Tarjetas.objects.annotate(
            total_transferencias_egreso_mes=Round(
                Coalesce(
                    Sum(
                        "transferenciastarjetas__cantidad",
                        filter=Q(
                            transferenciastarjetas__created_at__month=datetime.now().month,
                            transferenciastarjetas__tipo=TipoTranferenciaChoices.EGRESO,
                        ),
                    ),
                    Value(Decimal(0)),
                ),
                2,
            ),
            total_transferencias_ingreso_mes=Round(
                Coalesce(
                    Sum(
                        "transferenciastarjetas__cantidad",
                        filter=Q(
                            transferenciastarjetas__created_at__month=datetime.now().month,
                            transferenciastarjetas__tipo=TipoTranferenciaChoices.INGRESO,
                        ),
                    ),
                    Value(Decimal(0)),
                ),
                2,
            ),
            total_transferencias_egreso_dia=Round(
                Coalesce(
                    Sum(
                        "transferenciastarjetas__cantidad",
                        filter=Q(
                            transferenciastarjetas__created_at=datetime.now(),
                            transferenciastarjetas__tipo=TipoTranferenciaChoices.EGRESO,
                        ),
                    ),
                    Value(Decimal(0)),
                ),
                2,
            ),
            total_transferencias_ingreso_dia=Round(
                Coalesce(
                    Sum(
                        "transferenciastarjetas__cantidad",
                        filter=Q(
                            transferenciastarjetas__created_at=datetime.now(),
                            transferenciastarjetas__tipo=TipoTranferenciaChoices.INGRESO,
                        ),
                    ),
                    Value(Decimal(0)),
                ),
                2,
            ),
            isAvailable=Case(
                When(
                    Q(total_transferencias_egreso_mes__gte=120000)
                    | Q(total_transferencias_ingreso_mes__gte=120000)
                    | Q(total_transferencias_egreso_dia__gte=80000)
                    | Q(total_transferencias_ingreso_dia__gte=80000),
                    then=Value(False),
                ),
                default=Value(True),
                output_field=BooleanField(),
            ),
        ).all()

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
            "ventas": ventas,
            "productos_elaboraciones": productos_elaboraciones,
            "tarjetas": tarjetas,
        }

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

        gastos_variables = (
            Gastos.objects.filter(
                tipo=GastosChoices.VARIABLE,
                created_at__date__range=(parse_desde, parse_hasta),
                area_venta=None,
                is_cafeteria=True,
            ).aggregate(total=Sum("cantidad"))["total"]
            or 0
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

        subtotal_productos = (
            productos.aggregate(subtotal=Sum(F("importe")))["subtotal"] or 0
        )
        subtotal_elaboraciones = (
            elaboraciones.aggregate(subtotal=Sum(F("importe")))["subtotal"] or 0
        )
        subtotal = subtotal_productos + subtotal_elaboraciones

        mano_obra = (
            elaboraciones.aggregate(mano_obra=Sum(F("mano_obra")))["mano_obra"] or 0
        )

        total_productos = (
            productos.aggregate(total=Sum(F("importe")) - costo_producto)["total"] or 0
        )
        total_elaboraciones = (
            elaboraciones.aggregate(total=Sum(F("importe")))["total"] or 0
        )
        total = total_productos + total_elaboraciones - mano_obra

        return {
            "productos": productos_sin_repeticion,
            "elaboraciones": elaboraciones_sin_repeticion,
            "total": total,
            "costo_producto": costo_producto,
            "subtotal": subtotal,
            "efectivo": efectivo,
            "transferencia": transferencia,
            "mano_obra": mano_obra,
            "gastos_variables": gastos_variables,
            "gastos_fijos": total_gastos_fijos,
        }

    @route.post("entradas/")
    def add_entrada_cafeteria(self, request, body: Add_Entrada_Cafeteria):
        body_dict = body.model_dump()

        usuario = get_object_or_404(User, pk=request.auth["id"])

        with transaction.atomic():

            entrada = Entradas_Cafeteria.objects.create(
                metodo_pago=body_dict["metodo_pago"],
                proveedor=body_dict["proveedor"],
                usuario=usuario,
                comprador=body_dict["comprador"],
            )
            for producto in body_dict["productos"]:
                producto_cafeteria = get_object_or_404(
                    Productos_Cafeteria, pk=producto.get("producto")
                )
                producto_cafeteria.inventario.cantidad += Decimal(
                    producto.get("cantidad")
                )
                producto_cafeteria.inventario.save()
                producto_entrada = Productos_Entradas_Cafeteria.objects.create(
                    producto=producto_cafeteria,
                    cantidad=producto.get("cantidad"),
                )
                entrada.productos.add(producto_entrada)

        return

    @route.post("productos/")
    def add_productos_cafeteria(self, request, body: Add_Producto_Cafeteria):
        body_dict = body.model_dump()

        producto = Productos_Cafeteria.objects.create(**body_dict)
        Inventario_Producto_Cafeteria.objects.create(producto=producto, cantidad=0)
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
                            Inventario_Producto_Cafeteria,
                            id=ingrediente.ingrediente.pk,
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
                        Inventario_Producto_Cafeteria, id=producto.pk
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

            if body.metodo_pago in [METODO_PAGO.MIXTO, METODO_PAGO.TRANSFERENCIA]:
                tarjeta = get_object_or_404(Tarjetas, id=body.tarjeta)
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
                suma_balance = (
                    Decimal(body_dict["transferencia"])
                    if body.metodo_pago == METODO_PAGO.MIXTO
                    else total_venta
                )
                TransferenciasTarjetas.objects.create(
                    tarjeta=tarjeta,
                    cantidad=total_venta,
                    descripcion=descripcion,
                    tipo=TipoTranferenciaChoices.INGRESO,
                    usuario=usuario,
                    venta_cafeteria=venta,
                )
                balance = BalanceTarjetas.objects.get(tarjeta=tarjeta)
                balance.valor += suma_balance
                balance.save()

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

    @route.delete("entradas/{id}/")
    def delete_entrada_cafeteria(self, id: int):
        entrada = get_object_or_404(Entradas_Cafeteria, id=id)
        with transaction.atomic():
            for producto in entrada.productos.all():
                inventario = get_object_or_404(
                    Inventario_Producto_Cafeteria, producto=producto.producto
                )
                if inventario.cantidad - producto.cantidad <= 0:
                    raise HttpError(400, "No hay productos suficientes")
                inventario.cantidad -= producto.cantidad
                inventario.save()

            entrada.delete()

    @route.delete("ventas/{id}/")
    def delete_ventas_cafeteria(self, id: int):
        with transaction.atomic():
            venta = get_object_or_404(Ventas_Cafeteria, id=id)

            total_venta = 0
            for producto_venta_cafeteria in venta.productos.all():
                inventario = get_object_or_404(
                    Inventario_Producto_Cafeteria,
                    producto=producto_venta_cafeteria.producto,
                )
                inventario.cantidad += producto_venta_cafeteria.cantidad
                inventario.save()
                if venta.metodo_pago in [METODO_PAGO.MIXTO, METODO_PAGO.TRANSFERENCIA]:
                    total_venta += (
                        producto_venta_cafeteria.cantidad
                        * producto_venta_cafeteria.producto.precio_venta
                    )

            for elaboracion_venta_cafeteria in venta.elaboraciones.all():
                for (
                    ingrediente_cantidad,
                ) in elaboracion_venta_cafeteria.producto.ingredientes_cantidad.all():
                    inventario = get_object_or_404(
                        Inventario_Producto_Cafeteria,
                        producto__id=ingrediente_cantidad.ingrediente.id,
                    )
                    inventario.cantidad += ingrediente_cantidad.cantidad
                    inventario.save()
                    if venta.metodo_pago in [
                        METODO_PAGO.MIXTO,
                        METODO_PAGO.TRANSFERENCIA,
                    ]:
                        total_venta += (
                            ingrediente_cantidad.cantidad
                            * ingrediente_cantidad.ingrediente.precio_venta
                        )

            if venta.metodo_pago in [METODO_PAGO.MIXTO, METODO_PAGO.TRANSFERENCIA]:
                balance = get_object_or_404(
                    BalanceTarjetas,
                    tarjeta__transferenciastarjetas__venta_cafeteria=venta,
                )
                balance.valor += total_venta
                balance.save()

                TransferenciasTarjetas.objects.get(venta_cafeteria=venta).delete()

            venta.delete()
