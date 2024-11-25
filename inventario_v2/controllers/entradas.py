from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    EntradaAlmacen,
    EntradaAlmacenCafeteria,
    Producto,
    SalidaAlmacen,
    SalidaAlmacenRevoltosa,
    User,
    Ventas,
    Categorias,
)
from ..schema import (
    AddEntradaSchema,
    AddEntradaCafeteria,
    EntradaAlmacenSchema,
    EntradaAlmacenCafeteriaEndpoint,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from typing import List
from django.db import transaction
from django.db.models import Count

from ..custom_permissions import isStaff


@api_controller("entradas/", tags=["Entradas"], permissions=[isStaff])
class EntradasController:

    @route.get("principal/", response=List[EntradaAlmacenSchema])
    def get_entradas(self):
        entradas = (
            EntradaAlmacen.objects.all()
            .annotate(cantidad=Count("producto"))
            .values(
                "id",
                "metodo_pago",
                "proveedor",
                "comprador",
                "usuario__username",
                "producto__info__descripcion",
                "created_at",
                "cantidad",
            )
            .order_by("-created_at")
        )
        return entradas

    @route.get("cafeteria/", response=EntradaAlmacenCafeteriaEndpoint)
    def get_entradas_cafeteria(self):
        entradas = EntradaAlmacenCafeteria.objects.all().order_by("-created_at")
        categoria_cafeteria = Categorias.objects.filter(nombre="Cafetería").first()
        productos = (
            ProductoInfo.objects.filter(categoria=categoria_cafeteria)
            .only("codigo", "descripcion")
            .distinct()
        )
        return {"entradas": entradas, "productos": productos}

    @route.post("")
    def addEntrada(self, request, data: AddEntradaSchema):
        dataDict = data.model_dump()

        producto_info = get_object_or_404(ProductoInfo, codigo=dataDict["productInfo"])
        user = get_object_or_404(User, pk=request.auth["id"])
        with transaction.atomic():
            entrada = EntradaAlmacen(
                metodo_pago=dataDict["metodoPago"],
                proveedor=dataDict["proveedor"],
                usuario=user,
                comprador=dataDict["comprador"],
            )
            entrada.save()

            response = []

            if dataDict["variantes"] and not dataDict["cantidad"]:

                for variante in dataDict["variantes"]:
                    color = variante.get("color")
                    numeros = variante.get("numeros", [])

                    productos_pa = []

                    for num in numeros:
                        numero = num.get("numero")
                        cantidad = num.get("cantidad", 0)

                        ids = []

                        productos = [
                            Producto(
                                info=producto_info,
                                color=color,
                                numero=numero,
                                entrada=entrada,
                            )
                            for _ in range(cantidad)
                        ]

                        ids = Producto.objects.bulk_create(productos)

                        formated_ids = (
                            f"{ids[0].id}-{ids[-1].id}" if len(ids) > 1 else ids[0].id
                        )
                        productos_pa.append({"numero": numero, "ids": formated_ids})

                    response.append({"color": color, "numeros": productos_pa})
                return response

            elif dataDict["cantidad"] and not dataDict["variantes"]:

                productos = [
                    Producto(
                        info=producto_info,
                        entrada=entrada,
                    )
                    for _ in range(dataDict["cantidad"])
                ]

                Producto.objects.bulk_create(productos)

                return

            else:
                raise HttpError(400, "Bad Request")

    @route.post("cafeteria/")
    def add_entrada_cafeteria(self, request, data: AddEntradaCafeteria):
        dataDict = data.model_dump()

        producto_info = get_object_or_404(ProductoInfo, pk=dataDict["producto"])
        user = get_object_or_404(User, pk=request.auth["id"])
        try:
            with transaction.atomic():
                EntradaAlmacenCafeteria.objects.create(
                    metodo_pago=dataDict["metodoPago"],
                    proveedor=dataDict["proveedor"],
                    usuario=user,
                    comprador=dataDict["comprador"],
                    cantidad=dataDict["cantidad"],
                    info_producto=producto_info,
                )

                productos = [
                    Producto(
                        info=producto_info,
                        almacen_cafeteria=True,
                    )
                    for _ in range(dataDict["cantidad"])
                ]

                Producto.objects.bulk_create(productos)

                return
        except Exception as e:
            return {"error": f"Error al crear la entrada: {str(e)}"}, 400

    @route.delete("{id}/")
    def deleteEntrada(self, request, id):
        try:
            with transaction.atomic():
                entrada = get_object_or_404(EntradaAlmacen, pk=id)

                productos = Producto.objects.filter(entrada=entrada)

                salidas = SalidaAlmacen.objects.filter(
                    producto__in=productos
                ).distinct()

                salidas_revoltosa = SalidaAlmacenRevoltosa.objects.filter(
                    producto__in=productos
                ).distinct()

                ventas = Ventas.objects.filter(producto__in=productos).distinct()

                ventas.delete()
                salidas.delete()
                salidas_revoltosa.delete()
                entrada.delete()

            return {"message": "Entrada y elementos relacionados eliminados con éxito"}
        except Exception as e:
            return {"error": f"Error al eliminar la entrada: {str(e)}"}, 400

    @route.delete("cafeteria/{id}/")
    def delete_entrada_cafeteria(self, id: int):
        try:
            with transaction.atomic():
                entrada = get_object_or_404(EntradaAlmacenCafeteria, pk=id)

                productos = Producto.objects.filter(
                    almacen_cafeteria=True,
                    almacen_revoltosa=False,
                    area_venta__isnull=True,
                    venta__isnull=True,
                    entrada__isnull=True,
                    salida__isnull=True,
                    salida_revoltosa__isnull=True,
                )

                if productos.count() < entrada.cantidad:
                    raise HttpError(400, "Algunos productos ya no están en el almacén")

                productos_to_delete = list(productos[: entrada.cantidad])
                for producto in productos_to_delete:
                    producto.delete()
                entrada.delete()

            return
        except Exception as e:
            raise HttpError(400, f"Error al eliminar la entrada: {str(e)}")
