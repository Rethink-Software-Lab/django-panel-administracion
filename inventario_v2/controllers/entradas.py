from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    EntradaAlmacen,
    Entradas_Cafeteria,
    Producto,
    SalidaAlmacen,
    SalidaAlmacenRevoltosa,
    User,
    Ventas,
    Categorias,
    Transacciones,
    TipoTranferenciaChoices,
    Cuentas,
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
        entradas = Entradas_Cafeteria.objects.all().order_by("-created_at")
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
        cuenta = get_object_or_404(Cuentas, pk=dataDict["cuenta"])

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
                            f"{ids[0].pk}-{ids[-1].pk}" if len(ids) > 1 else ids[0].pk
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
                    descripcion=f"[ENT] {total_zapatos}x {producto_info.descripcion}",
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
                    descripcion=f"[ENT] {dataDict['cantidad']}x {producto_info.descripcion}",
                )

                return

            else:
                raise HttpError(400, "Bad Request")

    @route.post("cafeteria/")
    def add_entrada_cafeteria(self, request, data: AddEntradaCafeteria):
        dataDict = data.model_dump()

        producto_info = get_object_or_404(ProductoInfo, pk=dataDict["producto"])
        user = get_object_or_404(User, pk=request.auth["id"])
        cuenta = get_object_or_404(Cuentas, pk=dataDict["cuenta"])
        try:
            with transaction.atomic():
                entrada = Entradas_Cafeteria.objects.create(
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

                cuenta.saldo -= dataDict["cantidad"] * producto_info.precio_costo
                cuenta.save()
                Transacciones.objects.create(
                    entrada_cafeteria=entrada,
                    usuario=user,
                    tipo=TipoTranferenciaChoices.EGRESO,
                    cuenta=cuenta,
                    cantidad=dataDict["cantidad"] * producto_info.precio_costo,
                    descripcion=f"[ENT] {dataDict['cantidad']}x {producto_info.descripcion}",
                )

                return
        except Exception as e:
            return {"error": f"Error al crear la entrada: {str(e)}"}, 400

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

    @route.delete("cafeteria/{id}/")
    def delete_entrada_cafeteria(self, id: int):
        try:
            with transaction.atomic():
                entrada = get_object_or_404(Entradas_Cafeteria, pk=id)

                transaccion = get_object_or_404(
                    Transacciones, entrada_cafeteria=entrada
                )
                cuenta = get_object_or_404(Cuentas, pk=transaccion.cuenta.pk)

                cuenta.saldo += transaccion.cantidad
                cuenta.save()

                transaccion.delete()

                productos = Producto.objects.filter(
                    almacen_cafeteria=True,
                    almacen_revoltosa=False,
                    area_venta__isnull=True,
                    venta__isnull=True,
                    entrada__isnull=True,
                    salida__isnull=True,
                    salida_revoltosa__isnull=True,
                )

                if (
                    productos.count() * productos[0].info.precio_costo
                ) < transaccion.cantidad:
                    raise HttpError(400, "Algunos productos ya no están en el almacén")

                cant_prod = transaccion.cantidad / productos[0].info.precio_costo
                productos_to_delete = list(productos[:cant_prod])
                for producto in productos_to_delete:
                    producto.delete()
                entrada.delete()

            return
        except Exception as e:
            raise HttpError(400, f"Error al eliminar la entrada: {str(e)}")
