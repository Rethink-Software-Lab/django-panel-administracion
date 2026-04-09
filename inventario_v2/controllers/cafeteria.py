from datetime import datetime

from inventario.models import (
    HistorialIngredienteReceta,
    HistorialRecetaElaboracion,
    User,
    Elaboraciones,
    Ingrediente_Cantidad,
    Productos_Cafeteria,
    PrecioElaboracion,
)
from inventario_v2.controllers.utils_reportes.reporte_ventas_cafeteria import (
    get_reporte_ventas_cafeteria,
)

from ..schema import (
    ElaboracionesEndpoint,
    Add_Elaboracion,
    CafeteriaReporteSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal


@api_controller("cafeteria/", tags=["Cafetería"], permissions=[])
class CafeteriaController:
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

    @route.put("elaboraciones/{id}/")
    def edit_elaboracion(self, request, id: int, body: Add_Elaboracion):
        usuario = get_object_or_404(User, id=request.auth["id"])

        with transaction.atomic():
            elaboracion = get_object_or_404(Elaboraciones, id=id)
            ultimo_precio_elaboracion = PrecioElaboracion.objects.filter(
                elaboracion=elaboracion
            ).first()

            ingredientes_antiguos = [
                {
                    "ingrediente": ing.ingrediente,
                    "cantidad": ing.cantidad
                }
                for ing in elaboracion.ingredientes_cantidad.all()
            ]

            elaboracion.nombre = body.nombre
            elaboracion.mano_obra = Decimal(body.mano_obra)

            if (
                ultimo_precio_elaboracion
                and ultimo_precio_elaboracion.precio != body.precio
            ):
                PrecioElaboracion.objects.create(
                    elaboracion=elaboracion, precio=body.precio, usuario=usuario
                )

            ingredientes_existentes_dict = {
                ingrediente.ingrediente.id: ingrediente
                for ingrediente in elaboracion.ingredientes_cantidad.all()
            }
            
            nuevos_ingredientes_ids = [ing.producto for ing in body.ingredientes]
            receta_modificada = False

            for ingrediente_nuevo in body.ingredientes:
                if ingrediente_nuevo.producto in ingredientes_existentes_dict:
                    ingrediente_existente = ingredientes_existentes_dict[ingrediente_nuevo.producto]
                    
                    if ingrediente_existente.cantidad != Decimal(ingrediente_nuevo.cantidad):
                        ingrediente_existente.cantidad = ingrediente_nuevo.cantidad
                        ingrediente_existente.save()
                        receta_modificada = True
                else:
                    producto = get_object_or_404(Productos_Cafeteria, pk=ingrediente_nuevo.producto)
                    ingrediente = Ingrediente_Cantidad.objects.create(
                        ingrediente=producto, cantidad=ingrediente_nuevo.cantidad
                    )
                    elaboracion.ingredientes_cantidad.add(ingrediente)
                    receta_modificada = True

            for ingrediente_existente_id, instancia_ingrediente in ingredientes_existentes_dict.items():
                if ingrediente_existente_id not in nuevos_ingredientes_ids:
                    elaboracion.ingredientes_cantidad.remove(instancia_ingrediente)
                    instancia_ingrediente.delete()
                    receta_modificada = True

            elaboracion.save()

            if receta_modificada:
                nueva_version = HistorialRecetaElaboracion.objects.create(
                    elaboracion=elaboracion,
                    usuario=usuario
                )
                
                for ing_antiguo in ingredientes_antiguos:
                    HistorialIngredienteReceta.objects.create(
                        historial_receta=nueva_version,
                        ingrediente=ing_antiguo["ingrediente"],
                        cantidad=ing_antiguo["cantidad"]
                    )

        return 

    @route.delete("elaboraciones/{id}/")
    def delete_elaboracion(self, id: int):
        elaboracion = get_object_or_404(Elaboraciones, id=id)
        for ingredientes_cantidad in elaboracion.ingredientes_cantidad.all():
            ingredientes_cantidad.delete()
        elaboracion.delete()
        return
