from datetime import datetime

from inventario.models import (
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

    @route.delete("elaboraciones/{id}/")
    def delete_elaboracion(self, id: int):
        elaboracion = get_object_or_404(Elaboraciones, id=id)
        for ingredientes_cantidad in elaboracion.ingredientes_cantidad.all():
            ingredientes_cantidad.delete()
        elaboracion.delete()
        return
