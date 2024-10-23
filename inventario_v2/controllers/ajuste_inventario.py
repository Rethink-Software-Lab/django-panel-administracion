from ninja.errors import HttpError
from inventario.models import (
    AreaVenta,
    ProductoInfo,
    Producto,
    User,
    AjusteInventario,
)
from ..schema import (
    AjustesModifySchema,
    AllAjustesSchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin
from django.db import transaction
import re
from django.db.models import Count


@api_controller("ajuste-inventario/", tags=["Ajuste Inventario"], permissions=[isAdmin])
class AjusteInventarioController:
    @route.get("", response=AllAjustesSchema)
    def get_all_ajustes(self):
        ajustes = AjusteInventario.objects.all().order_by("-id")
        ajustes_con_productos = []
        for ajuste in ajustes:
            productos = ajuste.productos.all()
            infos = (
                ProductoInfo.objects.filter(producto__in=productos)
                .annotate(total_transfers=Count("producto"))
                .distinct()
            )

            ajustes_con_productos.append(
                {
                    "id": ajuste.pk,
                    "created_at": ajuste.created_at,
                    "usuario": ajuste.usuario,
                    "motivo": ajuste.motivo,
                    "productos": infos,
                }
            )

        areas_ventas = AreaVenta.objects.all()
        productos_info = ProductoInfo.objects.filter(
            producto__venta__isnull=True,
            producto__ajusteinventario__isnull=True,
        ).distinct()
        return {
            "ajustes": ajustes_con_productos,
            "areas_ventas": areas_ventas,
            "productos_info": productos_info,
        }

    @route.post("")
    def addAjuste(self, request, body: AjustesModifySchema):
        body_dict = body.model_dump()

        usuario = get_object_or_404(User, pk=request.auth["id"])

        try:
            with transaction.atomic():
                new_products = []
                for producto in body_dict["productos"]:
                    product = get_object_or_404(ProductoInfo, pk=producto["producto"])
                    if (
                        producto["cantidad"]
                        and producto["area_venta"]
                        and not producto["zapatos_id"]
                    ):
                        if (
                            producto["area_venta"] != "almacen-principal"
                            and producto["area_venta"] != "almacen-revoltosa"
                        ):
                            filtro = Producto.objects.filter(
                                info=product,
                                area_venta=producto["area_venta"],
                                almacen_revoltosa=False,
                                venta__isnull=True,
                                ajusteinventario__isnull=True,
                            )[: producto["cantidad"]]

                        elif producto["area_venta"] == "almacen-principal":
                            filtro = Producto.objects.filter(
                                info=product,
                                area_venta__isnull=True,
                                almacen_revoltosa=False,
                                venta__isnull=True,
                                ajusteinventario__isnull=True,
                            )[: producto["cantidad"]]

                        elif producto["area_venta"] == "almacen-revoltosa":
                            filtro = Producto.objects.filter(
                                info=product,
                                area_venta__isnull=True,
                                almacen_revoltosa=True,
                                venta__isnull=True,
                                ajusteinventario__isnull=True,
                            )[: producto["cantidad"]]

                        if filtro.count() < producto["cantidad"]:
                            raise HttpError(
                                400,
                                f"No hay {product.descripcion} suficientes en {producto["area_venta"]} para esta acción",
                            )

                        for producto in filtro:
                            new_products.append(
                                Producto(
                                    id=producto.pk,
                                    info=product,
                                )
                            )

                    elif (
                        producto["zapatos_id"]
                        and not producto["cantidad"]
                        and not producto["area_venta"]
                    ):
                        zapatos_ids = re.split(r"[;,]", producto["zapatos_id"])

                        zapatos = Producto.objects.filter(
                            pk__in=zapatos_ids,
                            info=product,
                        )
                        if zapatos.count() < len(zapatos_ids):
                            raise HttpError(
                                400,
                                f"Algunos ids no pertenecen a {product.descripcion}.",
                            )

                        filtro_venta = zapatos.filter(
                            venta__isnull=True,
                            ajusteinventario__isnull=True,
                        )

                        if filtro_venta.count() < len(zapatos_ids):
                            raise HttpError(
                                400,
                                f"Algunos productos no estan disponibles.",
                            )

                        for zapato in filtro_venta:
                            new_products.append(
                                Producto(
                                    id=zapato.pk,
                                    info=product,
                                )
                            )

                ajuste = AjusteInventario.objects.create(
                    motivo=body_dict["motivo"], usuario=usuario
                )
                ajuste.productos.set(new_products)

            return
        except Exception as e:
            if isinstance(e, HttpError) and e.status_code == 400:
                raise
            raise HttpError(500, f"Error inesperado: {str(e)}")

    @route.delete("{id}/")
    def deleteAjuste(self, id: int):
        ajuste = get_object_or_404(AjusteInventario, pk=id)

        try:
            ajuste.delete()
            return
        except:
            raise HttpError(500, "Error inesperado.")
