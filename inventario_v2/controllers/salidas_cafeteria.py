from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    SalidaAlmacenRevoltosa,
    SalidaAlmacenCafeteria,
    Producto,
    User,
    AreaVenta,
)
from ..schema import (
    AddSalidaRevoltosaSchema,
    ProductoInfoSalidaAlmacenRevoltosaSchema,
    SalidaAlmacenCafeteriaSchemaEndpoint,
    AddSalidaCafeteriaSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count

from ..custom_permissions import isStaff


@api_controller("salidas-cafeteria/", tags=["SalidasCafeteria"], permissions=[isStaff])
class SalidasCafeteriaController:

    @route.get("", response=SalidaAlmacenCafeteriaSchemaEndpoint)
    def get_salidas_cafeteria(self):
        try:
            salidas = SalidaAlmacenCafeteria.objects.all().order_by("-created_at")

            productos = (
                ProductoInfo.objects.filter(
                    producto__area_venta__isnull=True,
                    producto__almacen_revoltosa=False,
                    producto__almacen_cafeteria=True,
                    producto__ajusteinventario__isnull=True,
                    producto__entrada__isnull=True,
                    producto__salida__isnull=True,
                    producto__salida_revoltosa__isnull=True,
                    producto__venta__isnull=True,
                )
                .only("codigo", "descripcion")
                .distinct()
            )

            return {"salidas": salidas, "productos": productos}
        except Exception as e:
            raise HttpError(500, f"Error al obtener las salidas: {str(e)}")

    @route.post("")
    def add_salida_cafeteria(self, request, data: AddSalidaCafeteriaSchema):
        dataDict = data.model_dump()

        producto_info = get_object_or_404(ProductoInfo, pk=dataDict["producto"])

        area_cafeteria = get_object_or_404(AreaVenta, nombre="Cafetería")

        usuario_search = get_object_or_404(User, pk=request.auth["id"])

        try:
            with transaction.atomic():
                cantidad = dataDict["cantidad"]

                productos = Producto.objects.filter(
                    venta__isnull=True,
                    area_venta__isnull=True,
                    almacen_revoltosa=False,
                    almacen_cafeteria=True,
                    salida__isnull=True,
                    salida_revoltosa__isnull=True,
                    entrada__isnull=True,
                    info=producto_info,
                    ajusteinventario__isnull=True,
                )[:cantidad]

                if productos.count() < cantidad:
                    raise HttpError(
                        400,
                        f"No hay {producto_info.descripcion} suficientes para esta accion",
                    )

                prods = [
                    Producto(
                        id=producto.pk,
                        area_venta=area_cafeteria,
                        almacen_cafeteria=False,
                    )
                    for producto in productos
                ]

                Producto.objects.bulk_update(
                    prods,
                    fields=["area_venta", "almacen_cafeteria"],
                )

                SalidaAlmacenCafeteria.objects.create(
                    usuario=usuario_search,
                    cantidad=cantidad,
                    info_producto=producto_info,
                )

                return

        except Exception as e:
            raise HttpError(400, f"Error al crear la salida. {str(e)}")

    @route.delete("{id}/")
    def delete_salida_cafeteria(self, id: int):
        salida = get_object_or_404(SalidaAlmacenCafeteria, pk=id)

        productos = Producto.objects.filter(
            salida_revoltosa__isnull=True,
            venta__isnull=True,
            salida__isnull=True,
            entrada__isnull=True,
            area_venta__nombre="Cafetería",
            almacen_revoltosa=False,
            almacen_cafeteria=False,
            info=salida.info_producto,
            ajusteinventario__isnull=True,
        )[: salida.cantidad]

        print(productos.count())

        if productos.count() < salida.cantidad:
            raise HttpError(
                400,
                "No hay suficientes productos para esta accion",
            )

        try:
            with transaction.atomic():

                productos_para_actualizar = [
                    Producto(id=producto.pk, area_venta=None, almacen_cafeteria=True)
                    for producto in productos
                ]

                Producto.objects.bulk_update(
                    productos_para_actualizar,
                    fields=["area_venta", "almacen_cafeteria"],
                )

                salida.delete()
            return
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")
