from datetime import datetime
from typing import List
from ninja.errors import HttpError
from inventario.models import (
    METODO_PAGO,
    FrecuenciaChoices,
    Gastos,
    GastosChoices,
    Inventario_Area_Cafeteria,
    User,
    Elaboraciones,
    Productos_Cafeteria,
    Inventario_Almacen_Cafeteria,
    Entradas_Cafeteria,
    Productos_Entradas_Cafeteria,
    Ventas_Cafeteria,
    Salidas_Cafeteria,
    Productos_Salidas_Cafeteria,
)
from inventario_v2.utils import (
    calcular_dias_laborables,
    obtener_dias_semana_rango,
    obtener_ultimo_dia_mes,
)
from ..schema import (
    Add_Salida_Cafeteria,
    Producto_Cafeteria_Schema,
    Entradas_Almacen_Cafeteria_Schema,
    Add_Entrada_Cafeteria,
    EndPointSalidasAlmacenCafeteria,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from django.db.models import Q, Sum, F, Case, When, IntegerField


@api_controller("almacen-cafeteria/", tags=["Almacen Cafeteria"], permissions=[])
class AlmacenCafeteriaController:
    @route.get("inventario/", response=List[Producto_Cafeteria_Schema])
    def get_inventario_cafeteria(self):

        productos = Productos_Cafeteria.objects.filter(
            inventario_almacen__cantidad__gt=0
        )

        return productos

    @route.get("entradas/", response=Entradas_Almacen_Cafeteria_Schema)
    def get_entradas_cafeteria(self):

        entradas = Entradas_Cafeteria.objects.prefetch_related("productos").order_by(
            "-created_at"
        )
        productos = Productos_Cafeteria.objects.all()

        return {"entradas": entradas, "productos": productos}

    @route.get("salidas/", response=EndPointSalidasAlmacenCafeteria)
    def get_salidas_almacen_cafeteria(self):

        salidas = Salidas_Cafeteria.objects.order_by("-created_at")
        productos = Productos_Cafeteria.objects.filter(
            inventario_almacen__cantidad__gt=0
        )

        return {"salidas": salidas, "productos": productos}

    # @route.get("reportes/", response=CafeteriaReporteSchema)
    # def get_reporte(
    #     self,
    #     desde: datetime = datetime.today(),
    #     hasta: datetime = datetime.today(),
    # ):
    #     parse_desde = desde.date()
    #     parse_hasta = hasta.date()

    #     dias_laborables = calcular_dias_laborables(parse_desde, parse_hasta)
    #     ultimo_dia_hasta = obtener_ultimo_dia_mes(parse_hasta)
    #     dias_semana = obtener_dias_semana_rango(parse_desde, parse_hasta)

    #     productos = Productos_Cafeteria.objects.filter(
    #         productos_ventas_cafeteria__ventas_cafeteria__created_at__date__range=(
    #             parse_desde,
    #             parse_hasta,
    #         )
    #     ).annotate(
    #         cantidad=F("productos_ventas_cafeteria__cantidad"),
    #         importe=F("cantidad") * F("precio_venta"),
    #     )

    #     elaboraciones = Elaboraciones.objects.filter(
    #         elaboraciones_ventas_cafeteria__ventas_cafeteria__created_at__date__range=(
    #             parse_desde,
    #             parse_hasta,
    #         )
    #     ).annotate(
    #         cantidad=F("elaboraciones_ventas_cafeteria__cantidad"),
    #         importe=F("cantidad") * F("precio"),
    #     )

    #     efectivo_productos = (
    #         productos.aggregate(
    #             efectivo=Sum(
    #                 F("importe"),
    #                 filter=Q(
    #                     productos_ventas_cafeteria__ventas_cafeteria__metodo_pago=METODO_PAGO.EFECTIVO
    #                 ),
    #             ),
    #         )["efectivo"]
    #         or 0
    #     )

    #     transferencia_productos = (
    #         productos.aggregate(
    #             transferencia=Sum(
    #                 F("importe"),
    #                 filter=Q(
    #                     productos_ventas_cafeteria__ventas_cafeteria__metodo_pago=METODO_PAGO.TRANSFERENCIA
    #                 ),
    #             ),
    #         )["transferencia"]
    #         or 0
    #     )

    #     efectivo_elaboraciones = (
    #         elaboraciones.aggregate(
    #             efectivo=Sum(
    #                 F("importe"),
    #                 filter=Q(
    #                     elaboraciones_ventas_cafeteria__ventas_cafeteria__metodo_pago=METODO_PAGO.EFECTIVO
    #                 ),
    #             ),
    #         )["efectivo"]
    #         or 0
    #     )

    #     transferencia_elaboraciones = (
    #         elaboraciones.aggregate(
    #             transferencia=Sum(
    #                 F("importe"),
    #                 filter=Q(
    #                     elaboraciones_ventas_cafeteria__ventas_cafeteria__metodo_pago=METODO_PAGO.TRANSFERENCIA
    #                 ),
    #             ),
    #         )["transferencia"]
    #         or 0
    #     )

    #     efectivo_y_transferencia_ventas = Ventas_Cafeteria.objects.filter(
    #         created_at__date__range=(
    #             parse_desde,
    #             parse_hasta,
    #         )
    #     ).aggregate(efectivo=Sum(F("efectivo")), transferencia=Sum(F("transferencia")))

    #     efectivo = (
    #         efectivo_productos
    #         + efectivo_elaboraciones
    #         + (efectivo_y_transferencia_ventas["efectivo"] or 0)
    #     )
    #     transferencia = (
    #         transferencia_productos
    #         + transferencia_elaboraciones
    #         + (efectivo_y_transferencia_ventas["transferencia"] or 0)
    #     )

    #     costo_producto = (
    #         productos.aggregate(costo_producto=Sum(F("cantidad") * F("precio_costo")))[
    #             "costo_producto"
    #         ]
    #         or 0
    #     )

    #     gastos_variables = (
    #         Gastos.objects.filter(
    #             tipo=GastosChoices.VARIABLE,
    #             created_at__date__range=(parse_desde, parse_hasta),
    #             area_venta=None,
    #             is_cafeteria=True,
    #         ).aggregate(total=Sum("cantidad"))["total"]
    #         or 0
    #     )

    #     gastos_fijos = Gastos.objects.filter(
    #         tipo=GastosChoices.FIJO,
    #         created_at__date__lte=parse_hasta,
    #         area_venta=None,
    #         is_cafeteria=True,
    #     ).annotate(
    #         dia_mes_ajustado=Case(
    #             When(dia_mes__gt=ultimo_dia_hasta, then=ultimo_dia_hasta),
    #             default=F("dia_mes"),
    #             output_field=IntegerField(),
    #         )
    #     )

    #     gastos_fijos_mensuales = (
    #         gastos_fijos.filter(
    #             frecuencia=FrecuenciaChoices.MENSUAL,
    #             dia_mes_ajustado__range=(parse_desde.day, parse_hasta.day + 1),
    #         ).aggregate(total=Sum("cantidad"))["total"]
    #         or 0
    #     )

    #     gastos_fijos_semanales = gastos_fijos.filter(
    #         frecuencia=FrecuenciaChoices.SEMANAL,
    #         dia_semana__in=dias_semana,
    #     )

    #     total_gastos_fijos_semanales = sum(
    #         gasto.cantidad * dias_semana.get(gasto.dia_semana, 0)
    #         for gasto in gastos_fijos_semanales
    #     )

    #     gastos_lunes_sabado = (
    #         gastos_fijos.filter(frecuencia=FrecuenciaChoices.LUNES_SABADO).aggregate(
    #             total=Sum("cantidad")
    #         )["total"]
    #         or 0
    #     )

    #     total_gastos_lunes_sabado = gastos_lunes_sabado * dias_laborables

    #     total_gastos_fijos = (
    #         gastos_fijos_mensuales
    #         + total_gastos_fijos_semanales
    #         + total_gastos_lunes_sabado
    #     )

    #     # Recorrer productos y elaboraciones para evitar repeticiones
    #     productos_sin_repeticion = []
    #     elaboraciones_sin_repeticion = []
    #     for producto in productos:
    #         if producto not in productos_sin_repeticion:
    #             productos_sin_repeticion.append(producto)
    #         else:
    #             productos_sin_repeticion[
    #                 productos_sin_repeticion.index(producto)
    #             ].cantidad += producto.cantidad
    #             productos_sin_repeticion[
    #                 productos_sin_repeticion.index(producto)
    #             ].importe += producto.importe

    #     for elaboracion in elaboraciones:
    #         if elaboracion not in elaboraciones_sin_repeticion:
    #             elaboraciones_sin_repeticion.append(elaboracion)
    #         else:
    #             elaboraciones_sin_repeticion[
    #                 elaboraciones_sin_repeticion.index(elaboracion)
    #             ].cantidad += elaboracion.cantidad
    #             elaboraciones_sin_repeticion[
    #                 elaboraciones_sin_repeticion.index(elaboracion)
    #             ].importe += elaboracion.importe

    #     subtotal_productos = (
    #         productos.aggregate(subtotal=Sum(F("importe")))["subtotal"] or 0
    #     )
    #     subtotal_elaboraciones = (
    #         elaboraciones.aggregate(subtotal=Sum(F("importe")))["subtotal"] or 0
    #     )
    #     subtotal = subtotal_productos + subtotal_elaboraciones

    #     mano_obra = (
    #         elaboraciones.aggregate(mano_obra=Sum(F("mano_obra")))["mano_obra"] or 0
    #     )

    #     total_productos = (
    #         productos.aggregate(total=Sum(F("importe")) - costo_producto)["total"] or 0
    #     )
    #     total_elaboraciones = (
    #         elaboraciones.aggregate(total=Sum(F("importe")))["total"] or 0
    #     )
    #     total = total_productos + total_elaboraciones - mano_obra

    #     return {
    #         "productos": productos_sin_repeticion,
    #         "elaboraciones": elaboraciones_sin_repeticion,
    #         "total": total,
    #         "costo_producto": costo_producto,
    #         "subtotal": subtotal,
    #         "efectivo": efectivo,
    #         "transferencia": transferencia,
    #         "mano_obra": mano_obra,
    #         "gastos_variables": gastos_variables,
    #         "gastos_fijos": total_gastos_fijos,
    #     }

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
                producto_cafeteria.inventario_almacen.cantidad += Decimal(
                    producto.get("cantidad")
                )
                producto_cafeteria.inventario_almacen.save()
                producto_entrada = Productos_Entradas_Cafeteria.objects.create(
                    producto=producto_cafeteria,
                    cantidad=producto.get("cantidad"),
                )
                entrada.productos.add(producto_entrada)

        return

    @route.post("salidas/")
    def add_salida_cafeteria(self, request, body: Add_Salida_Cafeteria):
        body_dict = body.model_dump()

        usuario = get_object_or_404(User, id=request.auth["id"])
        with transaction.atomic():
            salida = Salidas_Cafeteria.objects.create(
                usuario=usuario,
            )
            for producto in body_dict["productos"]:
                producto_cafeteria = get_object_or_404(
                    Productos_Cafeteria, pk=producto["producto"]
                )
                producto_almacen = Inventario_Almacen_Cafeteria.objects.get(
                    producto=producto_cafeteria
                )
                producto_area = Inventario_Area_Cafeteria.objects.get(
                    producto=producto_cafeteria
                )
                if producto_almacen.cantidad < producto["cantidad"]:
                    raise HttpError(
                        400,
                        f"No hay suficiente {producto_almacen.producto.nombre} en almacen.",
                    )
                producto_almacen.cantidad -= producto["cantidad"]
                producto_area.cantidad += producto["cantidad"]
                producto_almacen.save()
                producto_area.save()
                producto_salida = Productos_Salidas_Cafeteria.objects.create(
                    producto=producto_cafeteria,
                    cantidad=producto["cantidad"],
                )
                salida.productos.add(producto_salida)

        salida.save()
        return

    @route.delete("entradas/{id}/")
    def delete_entrada_cafeteria(self, id: int):
        entrada = get_object_or_404(Entradas_Cafeteria, id=id)
        with transaction.atomic():
            for producto in entrada.productos.all():
                inventario = get_object_or_404(
                    Inventario_Almacen_Cafeteria, producto=producto.producto
                )
                if inventario.cantidad - producto.cantidad < 0:
                    raise HttpError(400, "No hay productos suficientes")
                inventario.cantidad -= producto.cantidad
                inventario.save()

            entrada.delete()

    @route.delete("salidas/{id}/")
    def delete_salidas_cafeteria(self, id: int):
        salida = get_object_or_404(Salidas_Cafeteria, id=id)
        with transaction.atomic():
            for producto in salida.productos.all():
                inventario_almacen = get_object_or_404(
                    Inventario_Almacen_Cafeteria, producto=producto.producto
                )
                inventario_area = get_object_or_404(
                    Inventario_Area_Cafeteria, producto=producto.producto
                )
                if inventario_area.cantidad - producto.cantidad < 0:
                    raise HttpError(400, "No hay productos suficientes")
                inventario_area.cantidad -= producto.cantidad
                inventario_almacen.cantidad += producto.cantidad
                inventario_area.save()
                inventario_almacen.save()

            salida.delete()
