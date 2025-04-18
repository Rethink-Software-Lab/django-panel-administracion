from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    EntradaAlmacen,
    Producto,
    SalidaAlmacen,
    SalidaAlmacenRevoltosa,
    User,
    Ventas,
    Transacciones,
    TipoTranferenciaChoices,
    Cuentas,
)
from ..schema import (
    AddEntradaSchema,
    EntradaAlmacenSchema,
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

    @route.post("")
    def addEntrada(self, request, data: AddEntradaSchema):
        dataDict = data.model_dump()

        producto_info = get_object_or_404(ProductoInfo, codigo=dataDict["productInfo"])
        user = get_object_or_404(User, pk=request.auth["id"])
        cuenta = get_object_or_404(Cuentas, pk=dataDict["cuenta"])

        try:
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

                    total_zapatos = 0

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

                            total_zapatos += cantidad

                            ids = Producto.objects.bulk_create(productos)

                            formated_ids = (
                                f"{ids[0].pk}-{ids[-1].pk}"
                                if len(ids) > 1
                                else ids[0].pk
                            )
                            productos_pa.append({"numero": numero, "ids": formated_ids})

                        response.append({"color": color, "numeros": productos_pa})

                    cuenta.saldo -= total_zapatos * producto_info.precio_costo
                    cuenta.save()
                    Transacciones.objects.create(
                        entrada=entrada,
                        usuario=user,
                        tipo=TipoTranferenciaChoices.EGRESO,
                        cuenta=cuenta,
                        cantidad=total_zapatos * producto_info.precio_costo,
                        descripcion=(
                            f"[ENT] {total_zapatos}x {producto_info.descripcion[:38]}..."
                            if len(producto_info.descripcion) > 38
                            else f"[ENT] {total_zapatos}x {producto_info.descripcion}"
                        ),
                    )

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

                    cuenta.saldo -= dataDict["cantidad"] * producto_info.precio_costo
                    cuenta.save()
                    Transacciones.objects.create(
                        entrada=entrada,
                        usuario=user,
                        tipo=TipoTranferenciaChoices.EGRESO,
                        cuenta=cuenta,
                        cantidad=dataDict["cantidad"] * producto_info.precio_costo,
                        descripcion=(
                            f"[ENT] {dataDict['cantidad']}x {producto_info.descripcion[:38]}..."
                            if len(producto_info.descripcion) > 38
                            else f"[ENT] {dataDict['cantidad']}x {producto_info.descripcion}"
                        ),
                    )

                    return

                else:
                    raise HttpError(400, "Bad Request")

        except Exception as e:
            print(f"Error en la transacción: {str(e)}")
            raise HttpError(400, "Bad Request")

    @route.delete("{id}/")
    def deleteEntrada(self, request, id: int):
        try:
            with transaction.atomic():
                entrada = get_object_or_404(EntradaAlmacen, pk=id)

                transaccion = get_object_or_404(Transacciones, entrada=entrada)
                cuenta = get_object_or_404(Cuentas, pk=transaccion.cuenta.pk)

                cuenta.saldo += transaccion.cantidad
                cuenta.save()

                transaccion.delete()

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
