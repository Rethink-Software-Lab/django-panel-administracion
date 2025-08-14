from ninja.errors import HttpError
from inventario.models import Transferencia, AreaVenta, ProductoInfo, Producto, User
from ..schema import (
    TransferenciasModifySchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin
from django.db import transaction
import re


@api_controller("transferencias/", tags=["Transferencias"], permissions=[isAdmin])
class TransferenciasController:
    @route.post("")
    def addTransferencia(self, request, body: TransferenciasModifySchema):
        body_dict = body.model_dump()

        area_origen = get_object_or_404(AreaVenta, pk=body_dict["de"])
        area_destino = get_object_or_404(AreaVenta, pk=body_dict["para"])
        usuario = get_object_or_404(User, pk=request.auth["id"])

        try:
            with transaction.atomic():
                new_products = []
                for producto in body_dict["productos"]:
                    product = get_object_or_404(ProductoInfo, pk=producto["producto"])
                    if producto["cantidad"] and not producto["zapatos_id"]:
                        filtro = Producto.objects.filter(
                            info=product,
                            area_venta=area_origen,
                            almacen_revoltosa=False,
                            venta__isnull=True,
                            ajusteinventario__isnull=True,
                        )[: producto["cantidad"]]

                        if filtro.count() < producto["cantidad"]:
                            raise HttpError(
                                400,
                                f"No hay {product.descripcion} suficientes en {area_origen.nombre} para esta acción",
                            )

                        for producto in filtro:
                            new_products.append(
                                Producto(
                                    id=producto.pk,
                                    area_venta=area_destino,
                                )
                            )

                    elif producto["zapatos_id"] and not producto["cantidad"]:
                        zapatos_ids = re.split(r"[;,]", producto["zapatos_id"])

                        zapatos = Producto.objects.filter(
                            pk__in=zapatos_ids,
                            info=product,
                            area_venta=area_origen,
                            almacen_revoltosa=False,
                            venta__isnull=True,
                            ajusteinventario__isnull=True,
                        )
                        if zapatos.count() < len(zapatos_ids):
                            raise HttpError(
                                400,
                                f"No hay {product.descripcion} suficientes en {area_origen.nombre} para esta acción",
                            )

                        for zapato in zapatos:
                            new_products.append(
                                Producto(
                                    id=zapato.pk,
                                    area_venta=area_destino,
                                )
                            )

                Producto.objects.bulk_update(
                    new_products,
                    fields=["area_venta"],
                )

                transferencia = Transferencia.objects.create(
                    de=area_origen, para=area_destino, usuario=usuario
                )
                transferencia.productos.set(new_products)

            return
        except Exception as e:
            if isinstance(e, HttpError) and e.status_code == 400:
                raise
            raise HttpError(500, f"Error inesperado: {str(e)}")

    @route.delete("{id}/")
    def deleteTransferencia(self, id: int):
        transferencia = get_object_or_404(Transferencia, pk=id)
        productos = transferencia.productos.all()
        productos_to_update = Producto.objects.filter(
            pk__in=productos.values_list("id", flat=True),
            area_venta=transferencia.para,
            venta__isnull=True,
            almacen_revoltosa=False,
            ajusteinventario__isnull=True,
        )

        if productos_to_update.count() != productos.count():
            raise HttpError(
                400, "Alguno productos ya no se encuentran en el área de venta."
            )
        try:
            productos_to_update.update(area_venta=transferencia.de)
            transferencia.delete()
            return
        except:
            raise HttpError(500, "Error inesperado.")
