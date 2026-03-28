from decimal import Decimal
from ninja.errors import HttpError
from inventario.models import (
    User,
    Merma,
    Productos_Cafeteria,
    Elaboraciones,
    Inventario_Area_Cafeteria,
    Inventario_Almacen_Cafeteria,
    Elaboraciones_Cantidad_Merma,
    Productos_Cantidad_Merma,
)
from ..schema import (
    AddMerma,
    EndpointMerma,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count


@api_controller("merma/", tags=["Merma"], permissions=[])
class MermaController:

    @route.post("")
    def add_merma(self, request, body: AddMerma):
        usuario = get_object_or_404(User, pk=request.auth["id"])

        try:
            with transaction.atomic():
                merma = Merma.objects.create(
                    is_almacen=(
                        True if body.localizacion == "almacen-cafeteria" else False
                    ),
                    usuario=usuario,
                )
                for producto in body.productos:
                    if producto.isElaboracion:
                        elaboracion = get_object_or_404(
                            Elaboraciones, id=producto.producto
                        )
                        for ingrediente in elaboracion.ingredientes_cantidad.all():
                            if body.localizacion == "almacen-cafeteria":
                                inventario = get_object_or_404(
                                    Inventario_Almacen_Cafeteria,
                                    producto=ingrediente.ingrediente,
                                )
                            elif body.localizacion == "cafeteria":
                                inventario = get_object_or_404(
                                    Inventario_Area_Cafeteria,
                                    producto=ingrediente.ingrediente,
                                )

                            if inventario.cantidad < ingrediente.cantidad * Decimal(
                                producto.cantidad
                            ):
                                raise HttpError(
                                    400,
                                    f"No hay suficiente {ingrediente.ingrediente.nombre}.",
                                )

                            inventario.cantidad -= ingrediente.cantidad * Decimal(
                                producto.cantidad
                            )
                            inventario.save()
                        new_elaboracion = Elaboraciones_Cantidad_Merma.objects.create(
                            producto=elaboracion,
                            cantidad=producto.cantidad,
                        )
                        merma.elaboraciones.add(new_elaboracion)
                    else:
                        product = get_object_or_404(
                            Productos_Cafeteria, pk=producto.producto
                        )
                        if body.localizacion == "almacen-cafeteria":
                            inventario = get_object_or_404(
                                Inventario_Almacen_Cafeteria,
                                producto=product,
                            )
                        elif body.localizacion == "cafeteria":
                            inventario = get_object_or_404(
                                Inventario_Area_Cafeteria,
                                producto=product,
                            )
                        if inventario.cantidad < Decimal(producto.cantidad):
                            raise HttpError(
                                400,
                                f"No hay suficiente {product.nombre}.",
                            )

                        inventario.cantidad -= Decimal(producto.cantidad)
                        inventario.save()
                        new_producto = Productos_Cantidad_Merma.objects.create(
                            producto=product,
                            cantidad=producto.cantidad,
                        )
                        merma.productos.add(new_producto)

            return
        except Exception as e:
            if isinstance(e, HttpError) and e.status_code == 400:
                raise
            raise HttpError(500, f"Error inesperado: {str(e)}")

    @route.delete("{id}/")
    def deleteMerma(self, id: int):
        merma = get_object_or_404(Merma, pk=id)

        try:
            with transaction.atomic():
                for producto in merma.productos.all():
                    if merma.is_almacen:
                        inventario = get_object_or_404(
                            Inventario_Almacen_Cafeteria,
                            producto=producto.producto,
                        )
                    else:
                        inventario = get_object_or_404(
                            Inventario_Area_Cafeteria,
                            producto=producto.producto,
                        )

                    inventario.cantidad += producto.cantidad
                    inventario.save()

                for elaboracion in merma.elaboraciones.all():
                    for ingrediente in elaboracion.producto.ingredientes_cantidad.all():
                        if merma.is_almacen:
                            inventario = get_object_or_404(
                                Inventario_Almacen_Cafeteria,
                                producto=ingrediente.ingrediente,
                            )
                        else:
                            inventario = get_object_or_404(
                                Inventario_Area_Cafeteria,
                                producto=ingrediente.ingrediente,
                            )

                        inventario.cantidad += ingrediente.cantidad * Decimal(
                            elaboracion.cantidad
                        )
                        inventario.save()

                merma.delete()
            return
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")
