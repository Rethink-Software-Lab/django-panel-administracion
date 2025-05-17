import tempfile
from ninja import File
from PIL import Image as IMG
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from ninja.files import UploadedFile
from inventario.models import (
    Categorias,
    Image,
    ProductoInfo,
    Producto,
    Ventas,
    SalidaAlmacen,
    SalidaAlmacenRevoltosa,
    EntradaAlmacen,
    Cuentas,
    HistorialPrecioCostoSalon,
    HistorialPrecioVentaSalon,
    User,
)
from ..schema import (
    ResponseEntradasPrinciapl,
    AddProductoSchema,
    UpdateProductoSchema,
    # ProductoWithCategotiaSchema,
)
from ninja_extra import api_controller, route
from typing import Optional
import cloudinary.uploader
from django.db import transaction
from django.db.models import F
from ..custom_permissions import isAuthenticated

# TODO:
#      * Permisos => Admin y Vendedor de la area de venta
#      * Endpoint /productos?area_venta=id
#


@api_controller("productos", tags=["Productos"], permissions=[isAuthenticated])
class ProductoController:

    @route.get("", response=ResponseEntradasPrinciapl)
    def getProductos(self):

        producto_info = ProductoInfo.objects.all().order_by("-id")
        cuentas = Cuentas.objects.all()

        return {"productos": producto_info, "cuentas": cuentas}

    # @route.get("/with-categorias/", response=ProductoWithCategotiaSchema)
    # def get_productos_with_categoria(self):
    #     producto_info = (
    #         ProductoInfo.objects.select_related(
    #             "precio_costo", "precio_venta", "categoria"
    #         )
    #         .values(
    #             "id",
    #             "descripcion",
    #             "categoria",
    #             "pago_trabajador",
    #             "precio_costo__precio",
    #             "precio_venta__precio",
    #         )
    #         .annotate(
    #             precio_costo=F("precio_costo__precio"),
    #             precio_venta=F("precio_venta__precio"),
    #         )
    #         .order_by("-id")
    #     )
    #     categorias = Categorias.objects.all()
    #     return {"productos": producto_info, "categorias": categorias}

    @route.post()
    def addProducto(
        self,
        request,
        data: AddProductoSchema,
        imagen: Optional[UploadedFile] = File(None),
    ):

        categoria_query = get_object_or_404(Categorias, pk=data.categoria)
        usuario = get_object_or_404(User, pk=request.auth["id"])

        productoInfo = ProductoInfo(
            descripcion=data.descripcion,
            categoria=categoria_query,
            pago_trabajador=data.pago_trabajador,
        )

        if imagen:
            try:
                # Abrir la imagen usando Pillow
                imagen = IMG.open(imagen)

                # Convertir a RGB si es necesario
                if imagen.mode in ("RGBA", "P"):
                    imagen = imagen.convert("RGB")

                    # Redimensionar la imagen (ajusta el tamaño según tus necesidades)
                    ancho, alto = imagen.size
                    # Calcular la relación de aspecto
                    relacion_aspecto = ancho / alto

                    imagen = imagen.resize(
                        (800, round(800 / relacion_aspecto)), IMG.LANCZOS
                    )

                # Guardar la imagen optimizada en un archivo temporal
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".webp"
                ) as temp_file:
                    imagen.save(temp_file.name, quality=60)
                    temp_file.seek(0)

                    # Subir la imagen optimizada a Cloudinary
                    response = cloudinary.uploader.upload(
                        temp_file.name, asset_folder="/dashboard_valero"
                    )
                    # Actualizar el campo de imagen con la URL de Cloudinary
                    imagen = Image(
                        url=response["secure_url"], public_id=response["public_id"]
                    )
                    imagen.save()
                    productoInfo.imagen = imagen
            except:
                raise HttpError(424, "Failed Dependecy")
        try:
            productoInfo.save()
            HistorialPrecioCostoSalon.objects.create(
                precio=data.precio_costo, usuario=usuario, producto_info=productoInfo
            )
            HistorialPrecioVentaSalon.objects.create(
                precio=data.precio_venta, usuario=usuario, producto_info=productoInfo
            )
        except Exception as e:
            raise HttpError(500, "Error inesperado")

        return {"success": True}

    @route.post("{id}/")
    def updateProducto(
        self,
        id: int,
        data: UpdateProductoSchema,
        imagen: Optional[UploadedFile] = File(None),
    ):

        producto = get_object_or_404(ProductoInfo, pk=id)
        categoria_query = get_object_or_404(Categorias, pk=data.categoria)

        producto.descripcion = data.descripcion
        producto.categoria = categoria_query
        producto.pago_trabajador = data.pago_trabajador

        if not imagen and data.deletePhoto:
            if producto.imagen:
                try:
                    cloudinary.uploader.destroy(producto.imagen.public_id)
                    img = get_object_or_404(Image, public_id=producto.imagen.public_id)
                    img.delete()
                    producto.imagen = None
                except:
                    raise HttpError(424, "Dependency fail")

        if imagen:
            try:
                # Abrir la imagen usando Pillow
                imagen = IMG.open(imagen)

                # Convertir a RGB si es necesario
                if imagen.mode in ("RGBA", "P"):
                    imagen = imagen.convert("RGB")

                    # Redimensionar la imagen (ajusta el tamaño según tus necesidades)
                    ancho, alto = imagen.size
                    # Calcular la relación de aspecto
                    relacion_aspecto = ancho / alto

                    imagen = imagen.resize(
                        (800, round(800 / relacion_aspecto)), IMG.LANCZOS
                    )

                # Guardar la imagen optimizada en un archivo temporal
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".webp"
                ) as temp_file:
                    imagen.save(temp_file.name, quality=60)
                    temp_file.seek(0)

                    # Subir la imagen optimizada a Cloudinary
                    response = cloudinary.uploader.upload(
                        temp_file.name, asset_folder="/dashboard_valero"
                    )
                    # Actualizar el campo de imagen con la URL de Cloudinary
                    imagen = Image(
                        url=response["secure_url"], public_id=response["public_id"]
                    )
                    imagen.save()
                    producto.imagen = imagen
            except:
                raise HttpError(424, "Failed Dependecy")

        try:
            producto.save()
        except:
            raise HttpError(500, "Error inesperado")

        return {"success": True}

    @route.delete("{id}/")
    def deleteProducto(self, id: int):
        productoInfo = get_object_or_404(ProductoInfo, pk=id)
        productos = Producto.objects.filter(info=productoInfo)
        entradas = EntradaAlmacen.objects.filter(producto__in=productos).distinct()
        salidas = SalidaAlmacen.objects.filter(producto__in=productos).distinct()
        salidas_revoltosa = SalidaAlmacenRevoltosa.objects.filter(
            producto__in=productos
        ).distinct()
        ventas = Ventas.objects.filter(producto__in=productos).distinct()

        with transaction.atomic():
            if productoInfo.imagen:
                try:
                    cloudinary.uploader.destroy(productoInfo.imagen.public_id)
                except:
                    raise HttpError(424, "Error al eliminar el recurso")

            ventas.delete()
            salidas.delete()
            salidas_revoltosa.delete()
            entradas.delete()
            productoInfo.delete()
            return {"success": True}
