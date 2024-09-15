import tempfile
from ninja import File
from PIL import Image as IMG
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from ninja.files import UploadedFile
from inventario.models import Categorias, Image, ProductoInfo, Producto
from ..schema import ProductoInfoSchema, AddProductoSchema, UpdateProductoSchema
from ninja_extra import api_controller, route
from typing import List, Optional
import cloudinary.uploader

from ..custom_permissions import isAuthenticated

# TODO:
#      * Permisos => Admin y Vendedor de la area de venta
#      * Endpoint /productos?area_venta=id
#


@api_controller("productos/", tags=["Productos"], permissions=[isAuthenticated])
class ProductoController:

    @route.get("", response=List[ProductoInfoSchema])
    def getProductos(self):

        producto_info = ProductoInfo.objects.all().order_by("-id")
        return producto_info

    @route.post()
    def addProducto(
        self, data: AddProductoSchema, imagen: Optional[UploadedFile] = File(None)
    ):
        dataDict = data.model_dump()

        categoria_query = get_object_or_404(Categorias, pk=dataDict["categoria"])

        productoInfo = ProductoInfo(
            codigo=dataDict["codigo"],
            descripcion=dataDict["descripcion"],
            categoria=categoria_query,
            pago_trabajador=(dataDict.get("pago_trabajador")),
            precio_costo=dataDict["precio_costo"],
            precio_venta=dataDict["precio_venta"],
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
        except Exception as e:
            if str(e).startswith("UNIQUE constraint"):
                raise HttpError(400, "El código debe ser único")
            else:
                raise HttpError(500, "Error inesperado")

        return {"success": True}

    @route.post("{id}/")
    def updateProducto(
        self,
        id: int,
        data: UpdateProductoSchema,
        imagen: Optional[UploadedFile] = File(None),
    ):
        dataDict = data.model_dump()

        producto = get_object_or_404(ProductoInfo, pk=id)
        categoria_query = get_object_or_404(Categorias, pk=dataDict["categoria"])

        if producto.codigo != dataDict["codigo"]:
            producto.codigo = dataDict["codigo"]

        producto.descripcion = dataDict["descripcion"]
        if producto.categoria != categoria_query:
            if Producto.objects.filter(info__categoria=categoria_query).exists():
                raise HttpError(
                    403,
                    "No es posible editar la categoría de un producto que tiene un producto asociado.",
                )
            producto.categoria = categoria_query

        producto.pago_trabajador = dataDict.get("pago_trabajador")
        producto.precio_costo = dataDict["precio_costo"]
        producto.precio_venta = dataDict["precio_venta"]

        if not dataDict["imagen"] and not imagen:
            if producto.imagen:
                try:
                    cloudinary.uploader.destroy(producto.imagen.public_id)
                    img = get_object_or_404(Image, public_id=producto.imagen.public_id)
                    img.delete()
                    producto.imagen = None
                except:
                    raise HttpError(424, "Dependency fail")

        if imagen and not dataDict["imagen"]:
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
        producto = get_object_or_404(ProductoInfo, pk=id)

        if producto.imagen:
            try:
                cloudinary.uploader.destroy(producto.imagen.public_id)
            except:
                raise HttpError(424, "Error al eliminar el recurso")

        try:
            producto.delete()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")
