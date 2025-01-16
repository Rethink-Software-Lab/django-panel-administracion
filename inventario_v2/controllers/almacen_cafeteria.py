from typing import List
from ninja.errors import HttpError
from inventario.models import (
    Inventario_Area_Cafeteria,
    User,
    Elaboraciones,
    Productos_Cafeteria,
    Inventario_Almacen_Cafeteria,
    Entradas_Cafeteria,
    Productos_Entradas_Cafeteria,
    Salidas_Cafeteria,
    Productos_Salidas_Cafeteria,
    Elaboraciones_Salidas_Almacen_Cafeteria,
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
        elaboraciones = Elaboraciones.objects.all()
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
            "salidas": salidas,
            "productos_elaboraciones": productos_elaboraciones,
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
                if producto.get("isElaboracion"):
                    elaboracion = get_object_or_404(
                        Elaboraciones, id=producto.get("producto")
                    )
                    for ingrediente in elaboracion.ingredientes_cantidad.all():
                        inventario_almacen = get_object_or_404(
                            Inventario_Almacen_Cafeteria,
                            producto__id=ingrediente.ingrediente.pk,
                        )
                        inventario_area = get_object_or_404(
                            Inventario_Area_Cafeteria,
                            producto__id=ingrediente.ingrediente.pk,
                        )

                        if (
                            inventario_almacen.cantidad
                            < ingrediente.cantidad * Decimal(producto["cantidad"])
                        ):
                            raise HttpError(
                                400,
                                f"No hay suficiente {ingrediente.ingrediente.nombre}.",
                            )

                        inventario_almacen.cantidad -= ingrediente.cantidad * Decimal(
                            producto["cantidad"]
                        )
                        inventario_area.cantidad += ingrediente.cantidad * Decimal(
                            producto["cantidad"]
                        )
                        inventario_almacen.save()
                        inventario_area.save()

                    elaboraciones_salida_cafeteria = (
                        Elaboraciones_Salidas_Almacen_Cafeteria.objects.create(
                            producto=elaboracion,
                            cantidad=producto.get("cantidad"),
                        )
                    )
                    salida.elaboraciones.add(elaboraciones_salida_cafeteria)
                else:
                    producto_cafeteria = get_object_or_404(
                        Productos_Cafeteria, pk=producto["producto"]
                    )
                    producto_almacen = Inventario_Almacen_Cafeteria.objects.get(
                        producto=producto_cafeteria
                    )
                    producto_area = Inventario_Area_Cafeteria.objects.get(
                        producto=producto_cafeteria
                    )
                    if producto_almacen.cantidad < Decimal(producto["cantidad"]):
                        raise HttpError(
                            400,
                            f"No hay suficiente {producto_almacen.producto.nombre} en almacen.",
                        )
                    producto_almacen.cantidad -= Decimal(producto["cantidad"])
                    producto_area.cantidad += Decimal(producto["cantidad"])
                    producto_almacen.save()
                    producto_area.save()
                    producto_salida = Productos_Salidas_Cafeteria.objects.create(
                        producto=producto_cafeteria,
                        cantidad=producto.get("cantidad"),
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
        try:
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

                for elaboracion_salida_almacen_cafeteria in salida.elaboraciones.all():
                    for (
                        ingrediente_cantidad
                    ) in (
                        elaboracion_salida_almacen_cafeteria.producto.ingredientes_cantidad.all()
                    ):
                        inventario_almacen = get_object_or_404(
                            Inventario_Almacen_Cafeteria,
                            producto=ingrediente_cantidad.ingrediente,
                        )
                        inventario_area = get_object_or_404(
                            Inventario_Area_Cafeteria,
                            producto=ingrediente_cantidad.ingrediente,
                        )
                        if inventario_area.cantidad - ingrediente_cantidad.cantidad < 0:
                            raise HttpError(400, "No hay productos suficientes")

                        inventario_area.cantidad -= (
                            ingrediente_cantidad.cantidad
                            * elaboracion_salida_almacen_cafeteria.cantidad
                        )
                        inventario_almacen.cantidad += (
                            ingrediente_cantidad.cantidad
                            * elaboracion_salida_almacen_cafeteria.cantidad
                        )
                        inventario_area.save()
                        inventario_almacen.save()

                salida.delete()
                return
        except Exception as e:
            raise HttpError(400, f"Error al eliminar salida: {e}")
