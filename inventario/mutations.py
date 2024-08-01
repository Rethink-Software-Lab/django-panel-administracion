from graphene import String, ID, Mutation, Field, ObjectType, Decimal
from graphene_file_upload.scalars import Upload
from graphql import GraphQLError
from django.shortcuts import get_object_or_404
from graphene.types.generic import GenericScalar
from django.db import transaction
import cloudinary.uploader
from PIL import Image as IMG
import tempfile
import re
from graphql_jwt.decorators import (
    login_required,
    staff_member_required,
    user_passes_test,
)
import graphql_jwt
from .types import *
from .models import *


class AddUser(Mutation):
    class Arguments:
        username = String(required=True)
        rol = String(required=True)
        area_venta = ID(required=False)
        password = String(required=True)

    user = Field(UserType)

    @staff_member_required
    def mutate(self, info, username, rol, password, area_venta=None):

        user = User.objects.create(username=username, rol=rol)

        if rol == "ADMIN":
            user.is_staff = True

        if area_venta is not None:
            area = get_object_or_404(AreaVenta, pk=area_venta)
            user.area_venta = area

        user.set_password(password)
        user.save()
        return AddUser(user=user)


class UpdateUser(Mutation):
    class Arguments:
        id = ID(required=True)
        username = String(required=True)
        rol = String(required=True)
        area_venta = ID(required=False)
        password = String(required=True)

    user = Field(UserType)

    @staff_member_required
    def mutate(self, info, id, username, rol, password, area_venta=None):
        try:
            user = get_object_or_404(User, pk=id)
            if not user.is_superuser:
                user.username = username
                user.rol = rol
                if password != "":
                    user.set_password(password)
                if area_venta is None:
                    user.area_venta = None
                else:
                    area = get_object_or_404(AreaVenta, pk=area_venta)
                    user.area_venta = area
                user.save()
                return UpdateUser(user=user)
            else:
                return GraphQLError("No tiene permisos para realizar esta acción")
        except User.DoesNotExist:
            return GraphQLError("El id no coincide con ningún usuario")
        except:
            return GraphQLError("Something went wrong XC")


class DeleteUser(Mutation):
    class Arguments:
        id = ID(required=True)

    message = String()

    @staff_member_required
    def mutate(self, info, id):
        try:
            user = get_object_or_404(User, pk=id)
            if not user.is_superuser:
                user.delete()
                return DeleteUser(message="Usuario eliminado con éxito")
            else:
                return GraphQLError("No tiene permisos para realizar esta acción")
        except User.DoesNotExist:
            return GraphQLError("El id no coincide con ningún usuario")
        except:
            return GraphQLError("Something went wrong XC")


class AddProductoInfo(Mutation):
    class Arguments:
        codigo = String(required=True)
        descripcion = String(required=True)
        categoria = String(required=True)
        imagen = Upload(required=False)
        precio_costo = Decimal(required=True)
        precio_venta = Decimal(required=True)

    productoInfo = Field(ProductInfoType)

    @login_required
    def mutate(
        self,
        info,
        codigo,
        descripcion,
        categoria,
        precio_costo,
        precio_venta,
        imagen=None,
    ):

        categoria_query = get_object_or_404(Categorias, pk=categoria)

        productoInfo = ProductoInfo(
            codigo=codigo,
            descripcion=descripcion,
            categoria=categoria_query,
            precio_costo=precio_costo,
            precio_venta=precio_venta,
        )

        try:
            if imagen is not None:
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
            pass
        productoInfo.save()
        return AddProductoInfo(productoInfo)


class UpdateProductoInfo(Mutation):
    class Arguments:
        id = ID(required=True)
        codigo = String(required=True)
        descripcion = String(required=True)
        categoria = String(required=True)
        imagen = Upload(required=False)
        precio_costo = Decimal(required=True)
        precio_venta = Decimal(required=True)

    productoInfo = Field(ProductInfoType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(
        self,
        info,
        id,
        codigo,
        descripcion,
        categoria,
        precio_costo,
        precio_venta,
        imagen=None,
    ):
        try:
            producto = get_object_or_404(ProductoInfo, pk=id)
            if producto.codigo != codigo:
                producto.codigo = codigo
            producto.descripcion = descripcion
            categoria_query = get_object_or_404(Categorias, pk=categoria)
            producto.categoria = categoria_query
            producto.precio_costo = precio_costo
            producto.precio_venta = precio_venta

            if imagen is not None:
                if producto.imagen is not None:
                    try:
                        cloudinary.uploader.destroy(producto.imagen.public_id)
                    except:
                        return GraphQLError("Error al eliminar el recurso")
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
                        producto.save()
                except:
                    producto.save()

            producto.save()
            return UpdateProductoInfo(productoInfo=producto)
        except Producto.DoesNotExist:
            return GraphQLError("Product not found")


class DeleteProductoInfo(Mutation):
    class Arguments:
        id = ID(required=True)

    message = String()

    @login_required
    def mutate(self, info, id):
        try:
            producto = get_object_or_404(ProductoInfo, pk=id)
            try:
                cloudinary.uploader.destroy(producto.imagen.public_id)
            except:
                return GraphQLError("Error al eliminar el recurso")
            producto.delete()
            return DeleteProductoInfo(message="Producto eliminado con éxito")
        except ProductoInfo.DoesNotExist:
            return GraphQLError("Product not found")
        except:
            return GraphQLError("Something went wrong XC")


class AddEntradaAlmacen(Mutation):
    class Arguments:
        metodo_pago = String(required=True)
        proveedor = String(required=True)
        variantes = GenericScalar()
        cantidad = Int()
        product_info = String(required=True)
        comprador = String(required=True)

    message = String()

    @user_passes_test(lambda user: user.rol in ["ADMIN", "ALMACENERO"])
    def mutate(
        self,
        info,
        metodo_pago,
        proveedor,
        product_info,
        comprador,
        variantes=None,
        cantidad=None,
    ):
        producto_info = ProductoInfo.objects.get(codigo=product_info)

        try:
            with transaction.atomic():

                entrada = EntradaAlmacen(
                    metodo_pago=metodo_pago,
                    proveedor=proveedor,
                    usuario=info.context.user,
                    comprador=comprador,
                )
                response = []
                if variantes and not cantidad:
                    if not isinstance(variantes, list):
                        raise GraphQLError(
                            "Formato corrupto: 'variante' debe ser <class: list> "
                        )

                    for variante in variantes:
                        color = variante.get("color")
                        numeros = variante.get("numeros", [])

                        productos_pa = []

                        for num in numeros:
                            numero = num.get("numero")
                            cantidad = num.get("cantidad", 0)

                            ids = []

                            for _ in range(cantidad):
                                producto = Producto(
                                    info=producto_info,
                                    color=color,
                                    numero=numero,
                                    entrada=entrada,
                                )
                                producto.save()
                                ids.append(producto.id)

                            array_ids = (
                                f"{ids[0]}-{ids[-1]}" if len(ids) > 1 else ids[0]
                            )
                            productos_pa.append({"numero": numero, "ids": array_ids})

                        response.append({"color": color, "numeros": productos_pa})
                    entrada.productos = response

                elif cantidad and not variantes:
                    entrada.productos = cantidad
                    productos_pa = []
                    ids = []
                    for _ in range(cantidad):
                        producto = Producto(
                            info=producto_info,
                            entrada=entrada,
                        )
                        producto.save()
                        ids.append(producto.id)

                    productos_pa = f"{ids[0]}-{ids[-1]}" if len(ids) > 1 else ids[0]

                else:
                    raise GraphQLError("Bad request")

                entrada.save()

        except Exception as e:
            raise GraphQLError("as")

        return AddEntradaAlmacen(message="ok")


class DeleteEntradaAlmacen(Mutation):
    class Arguments:
        id = ID(required=True)

    message = String()

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id):
        try:
            entrada = get_object_or_404(EntradaAlmacen, pk=id)
            entrada.delete()
            return DeleteEntradaAlmacen(message="Entrada eliminada con éxito")
        except EntradaAlmacen.DoesNotExist:
            return GraphQLError("Entrada no encontrada")
        except:
            return GraphQLError("Something went wrong XC")


class AddVentas(Mutation):
    class Arguments:
        productos = List(ID, required=True)
        area_venta = ID(required=True)
        metodo_pago = String(required=True)

    ventas = Field(VentasType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "VENDEDOR")
    def mutate(self, info, productos, area_venta, metodo_pago):
        if info.context.user.rol == "ADMIN" or info.context.user.area_venta.id == int(
            area_venta
        ):
            with transaction.atomic():
                area_venta = get_object_or_404(AreaVenta, pk=area_venta)
                venta = Ventas.objects.create(
                    area_venta=area_venta,
                    metodo_pago=metodo_pago,
                    usuario=info.context.user,
                )
                venta.save()

                productos = Producto.objects.filter(pk__in=productos)
                productos.update(venta=venta)
                return AddVentas(venta)
        else:
            return GraphQLError("No tienes permisos para relizar esta acción")


class UpdateVentas(Mutation):
    class Arguments:
        id = ID(required=True)
        productos = List(ID, required=True)
        area_venta = ID(required=True)
        metodo_pago = String(required=True)

    ventas = Field(VentasType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "VENDEDOR")
    def mutate(self, info, id, productos, area_venta, metodo_pago):
        if info.context.user.rol == "ADMIN" or info.context.user.area_venta.id == int(
            area_venta
        ):
            productos = Producto.objects.filter(pk__in=productos)
            ventas = get_object_or_404(Ventas, pk=id)
            area_venta = get_object_or_404(AreaVenta, pk=area_venta)

            ventas.area_venta = area_venta
            ventas.usuario = info.context.user
            ventas.metodo_pago = metodo_pago
            ventas.producto_set.set(productos)
            ventas.save()

            return UpdateVentas(ventas)

        return GraphQLError("No tienes permisos para relizar esta acción")


class DeleteVentas(Mutation):
    class Arguments:
        id = ID(required=True)

    message = String()

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "VENDEDOR")
    def mutate(self, info, id):
        try:
            ventas = get_object_or_404(Ventas, pk=id)

            if (
                info.context.user.rol == "ADMIN"
                or info.context.user.area_venta.id == ventas.area_venta.id
            ):
                ventas.delete()
                return DeleteVentas(message="Venta eliminada con éxito")
            return GraphQLError("No tienes permisos para relizar esta acción")

        except Ventas.DoesNotExist:
            return GraphQLError("Venta no encontrada")
        except:
            return GraphQLError("Something went wrong XC")


class AddAreaVenta(Mutation):
    class Arguments:
        nombre = String(required=True)
        color = String(required=True)

    area_venta = Field(AreaVentaType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, nombre, color):
        area_venta = AreaVenta.objects.create(nombre=nombre, color=color)
        area_venta.save()
        return AddAreaVenta(area_venta)


class UpdateAreaVenta(Mutation):
    class Arguments:
        id = ID(required=True)
        nombre = String(required=True)
        color = String(required=True)

    area_venta = Field(AreaVentaType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id, nombre, color):

        area_venta = get_object_or_404(AreaVenta, pk=id)
        area_venta.nombre = nombre
        area_venta.color = color
        area_venta.save()

        return UpdateAreaVenta(area_venta)


class DeleteAreaVenta(Mutation):
    class Arguments:
        id = ID(required=True)

    message = String()

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id):
        try:
            area_venta = get_object_or_404(AreaVenta, pk=id)
            area_venta.delete()
            return DeleteAreaVenta(message="Área de venta eliminada con éxito")
        except EntradaAlmacen.DoesNotExist:
            return GraphQLError("Área de venta no encontrada")
        except:
            return GraphQLError("Something went wrong XC")


class AddSalidaAlmacen(Mutation):
    class Arguments:
        productos = List(ID, required=True)
        area_venta = ID(required=True)

    salida_almacen = Field(SalidaAlmacenType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, productos, area_venta):

        productos = Producto.objects.filter(pk__in=productos)
        area_venta = get_object_or_404(AreaVenta, pk=area_venta)
        usuario_search = get_object_or_404(User, pk=info.context.user.id)
        try:
            salida = SalidaAlmacen.objects.create(
                area_venta=area_venta, usuario=usuario_search
            )

            salida.productos.set(productos)
            productos.update(area_venta=area_venta)

            return AddSalidaAlmacen(salida_almacen=salida)
        except:
            return GraphQLError("Algo salió mal XC")


class UpdateSalidaAlmacen(Mutation):
    class Arguments:
        id = ID(required=True)
        productos = List(ID, required=True)
        area_venta = ID(required=True)

    salida_almacen = Field(SalidaAlmacenType)

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id, productos, area_venta):

        productos = Producto.objects.filter(pk__in=productos)
        salida = get_object_or_404(SalidaAlmacen, pk=id)
        area_venta = get_object_or_404(AreaVenta, pk=area_venta)

        salida.area_venta = area_venta
        salida.usuario = info.context.user
        salida.productos.update(area_venta=None, in_stock=True)
        salida.save()

        salida.productos.set(productos)

        return UpdateSalidaAlmacen(salida_almacen=salida)


class DeleteSalidaAlmacen(Mutation):
    class Arguments:
        id = ID(required=True)

    message = String()

    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id):
        try:
            salida = get_object_or_404(SalidaAlmacen, pk=id)
            salida.productos.update(area_venta=None)
            salida.delete()
            return DeleteSalidaAlmacen(message="Salida eliminada con éxito")
        except EntradaAlmacen.DoesNotExist:
            return GraphQLError("Salida no encontrada")
        except:
            return GraphQLError("Something went wrong XC")


class ObtainJSONWebToken(graphql_jwt.JSONWebTokenMutation):
    user = Field(UserType)

    @classmethod
    def resolve(cls, root, info, **kwargs):
        return cls(user=info.context.user)


class Mutations(ObjectType):
    add_user = AddUser.Field()
    update_user = UpdateUser.Field()
    delete_user = DeleteUser.Field()
    add_producto_info = AddProductoInfo.Field()
    update_producto_info = UpdateProductoInfo.Field()
    delete_producto_info = DeleteProductoInfo.Field()
    add_entrada = AddEntradaAlmacen.Field()
    delete_entrada = DeleteEntradaAlmacen.Field()
    add_salida = AddSalidaAlmacen.Field()
    update_salida = UpdateSalidaAlmacen.Field()
    delete_salida = DeleteSalidaAlmacen.Field()
    add_area_venta = AddAreaVenta.Field()
    update_area_venta = UpdateAreaVenta.Field()
    delete_area_venta = DeleteAreaVenta.Field()
    add_venta = AddVentas.Field()
    update_venta = UpdateVentas.Field()
    delete_venta = DeleteVentas.Field()
    login = ObtainJSONWebToken.Field()
