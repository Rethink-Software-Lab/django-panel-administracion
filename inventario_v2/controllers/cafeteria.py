from datetime import datetime, timedelta
from django.utils import timezone
from typing import List
from inventario.models import (
    Inventario_Area_Cafeteria,
    User,
    Cuentas,
    TipoTranferenciaChoices,
    Elaboraciones,
    Ingrediente_Cantidad,
    Productos_Cafeteria,
    Inventario_Almacen_Cafeteria,
    Ventas_Cafeteria,
    PrecioElaboracion,
    CuentasChoices,
    HistorialPrecioCostoCafeteria,
    HistorialPrecioVentaCafeteria,
)
from inventario_v2.controllers.utils_reportes.reporte_ventas_cafeteria import (
    get_reporte_ventas_cafeteria,
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

        return get_reporte_ventas_cafeteria(parse_desde, parse_hasta)

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
