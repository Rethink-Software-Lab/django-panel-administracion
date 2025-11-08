from decimal import Decimal
from ninja.errors import HttpError
from inventario.models import (
    Cuentas,
    TipoTranferenciaChoices,
    Transacciones,
    User,
    Productos_Cafeteria,
    Elaboraciones,
    Inventario_Area_Cafeteria,
    Inventario_Almacen_Cafeteria,
    CuentaCasa,
    Elaboraciones_Cantidad_Cuenta_Casa,
    Productos_Cantidad_Cuenta_Casa,
)
from ..schema import (
    AddMerma,
    EndpointCuentaCasa,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count


@api_controller("cuenta-casa/", tags=["Cuenta Casa"], permissions=[])
class CuentaCasaController:
    @route.get("", response=EndpointCuentaCasa)
    def get_merma(self):
        cuenta_casa = (
            CuentaCasa.objects.all()
            .order_by("-created_at")
            .annotate(
                cantidad_productos=Count("productos"),
                cantidad_elaboraciones=Count("elaboraciones"),
            )
        )
        productos = Productos_Cafeteria.objects.all()
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
            "cuenta_casa": cuenta_casa,
            "productos_elaboraciones": productos_elaboraciones,
        }

    @route.post("")
    def add_cuenta_casa(self, request, body: AddMerma):
        usuario = get_object_or_404(User, pk=request.auth["id"])

        try:
            with transaction.atomic():
                cuenta_casa = CuentaCasa.objects.create(
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
                        mano_obra = elaboracion.mano_obra * Decimal(producto.cantidad)

                        caja_cafeteria = get_object_or_404(Cuentas, id=71)

                        Transacciones.objects.create(
                            cantidad=mano_obra,
                            usuario=usuario,
                            tipo=TipoTranferenciaChoices.PAGO_TRABAJADOR,
                            cuenta=caja_cafeteria,
                            descripcion=f"{producto.cantidad}x {elaboracion.nombre} - Cuenta Casa",
                            cuenta_casa=cuenta_casa,
                        )

                        caja_cafeteria.saldo -= mano_obra
                        caja_cafeteria.save()

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

                        new_elaboracion = (
                            Elaboraciones_Cantidad_Cuenta_Casa.objects.create(
                                producto=elaboracion,
                                cantidad=producto.cantidad,
                            )
                        )
                        cuenta_casa.elaboraciones.add(new_elaboracion)
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
                        new_producto = Productos_Cantidad_Cuenta_Casa.objects.create(
                            producto=product,
                            cantidad=producto.cantidad,
                        )
                        cuenta_casa.productos.add(new_producto)

            return
        except Exception as e:
            if isinstance(e, HttpError) and e.status_code == 400:
                raise
            raise HttpError(500, f"Error inesperado: {str(e)}")

    @route.delete("{id}/")
    def delete_cuenta_casa(self, id: int):
        cuenta_casa = get_object_or_404(CuentaCasa, pk=id)

        try:
            with transaction.atomic():
                for producto in cuenta_casa.productos.all():
                    if cuenta_casa.is_almacen:
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

                for elaboracion in cuenta_casa.elaboraciones.all():
                    for ingrediente in elaboracion.producto.ingredientes_cantidad.all():
                        if cuenta_casa.is_almacen:
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

                if cuenta_casa.elaboraciones.count() > 0:
                    transaccion = get_object_or_404(
                        Transacciones,
                        cuenta_casa=cuenta_casa,
                        tipo=TipoTranferenciaChoices.PAGO_TRABAJADOR,
                    )

                    caja_cafeteria = get_object_or_404(Cuentas, id=71)
                    caja_cafeteria.saldo += transaccion.cantidad
                    caja_cafeteria.save()

                cuenta_casa.delete()
            return
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")
