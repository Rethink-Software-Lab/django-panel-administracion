from ninja.errors import HttpError
from inventario.models import ProductoInfo, EntradaAlmacen, Producto, User
from ..schema import AddEntradaSchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404

from django.db import transaction

from ..custom_permissions import isStaff


@api_controller("entradas/", tags=["Entradas"], permissions=[isStaff])
class EntradasController:

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
