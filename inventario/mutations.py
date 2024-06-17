from graphene import String, ID, Mutation, Field, ObjectType, Decimal
from graphene_file_upload.scalars import Upload
from graphql import GraphQLError
from django.shortcuts import get_object_or_404
from graphene.types.generic import GenericScalar
import cloudinary.uploader 
from PIL import Image as IMG
import tempfile
import re
from graphql_jwt.decorators import login_required, staff_member_required, user_passes_test
import graphql_jwt
from .types import *
from .models import *

class AddUser(Mutation):
    class Arguments:
        username = String(required=True)
        rol = String(required=True)
        punto_venta = ID(required=False)
        password = String(required=True)

    user = Field(UserType)
    
    @staff_member_required
    def mutate(self, info, username, rol, password, punto_venta=None):
        
        user = User.objects.create(username=username, rol=rol)
        
        if rol == "ADMIN":
            user.is_staff = True

        if punto_venta is not None:
            user.punto_venta=punto_venta

        user.set_password(password)
        user.save()
        return AddUser(user=user)

class UpdateUser(Mutation):
    class Arguments:
        id = ID(required=True)
        username = String(required=True)
        rol = String(required=True)
        punto_venta = ID(required=False)
        password = String(required=True)

    user = Field(UserType)
    
    @staff_member_required
    def mutate(self, info, id, username, rol, password, punto_venta=None):
        try:
            user = get_object_or_404(User, pk=id)
            if not user.is_superuser:
                user.username = username
                user.rol = rol
                if password != '':
                    user.set_password(password)
                if punto_venta is not None:
                    user.punto_venta=punto_venta
                user.save()
                return UpdateUser(user=user)
            else:
                return GraphQLError('No tiene permisos para realizar esta acción')
        except User.DoesNotExist:
            return GraphQLError('El id no coincide con ningún usuario')
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
                return GraphQLError('No tiene permisos para realizar esta acción')
        except User.DoesNotExist:
            return GraphQLError('El id no coincide con ningún usuario')
        except:
            return GraphQLError("Something went wrong XC")
        
    
class AddProductoInfo(Mutation):
    class Arguments:
        codigo = String(required=True)
        descripcion = String(required=True)
        imagen = Upload(required=False)
        precio_costo = Decimal(required=True)
        precio_venta = Decimal(required=True)

    productoInfo = Field(ProductInfoType)
    
    @login_required
    def mutate(self, info, codigo, descripcion, precio_costo, precio_venta, imagen=None):
        print(imagen)
        
        productoInfo = ProductoInfo(codigo=codigo, descripcion=descripcion,
                                                   precio_costo=precio_costo, precio_venta=precio_venta)
        
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
                    
                    imagen = imagen.resize((800, round(800 / relacion_aspecto)), IMG.LANCZOS)

                # Guardar la imagen optimizada en un archivo temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as temp_file:
                    imagen.save(temp_file.name, quality=60)
                    temp_file.seek(0)
                
                # Subir la imagen optimizada a Cloudinary
                    response = cloudinary.uploader.upload(temp_file.name, asset_folder='/dashboard_valero')
                    # Actualizar el campo de imagen con la URL de Cloudinary
                    imagen = Image(url=response['secure_url'])
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
        imagen = Upload(required=False)
        precio_costo = Decimal(required=True)
        precio_venta = Decimal(required=True)

    productoInfo = Field(ProductInfoType)
    
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id, codigo, descripcion, precio_costo, precio_venta, imagen=None):
        try:
            producto = get_object_or_404(ProductoInfo, pk=id)
            if producto.codigo != codigo:
                producto.codigo=codigo
            producto.descripcion=descripcion
            producto.precio_costo=precio_costo
            producto.precio_venta=precio_venta
            producto.imagen = None
            if imagen is not None:
                try :
                    # Abrir la imagen usando Pillow
                    imagen = IMG.open(imagen)

                    # Convertir a RGB si es necesario
                    if imagen.mode in ("RGBA", "P"):
                        imagen = imagen.convert("RGB")

                    # Redimensionar la imagen (ajusta el tamaño según tus necesidades)
                    ancho, alto = imagen.size
                    # Calcular la relación de aspecto
                    relacion_aspecto = ancho / alto
                    
                    imagen = imagen.resize((800, round(800 / relacion_aspecto)), IMG.LANCZOS)

                    # Guardar la imagen optimizada en un archivo temporal
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as temp_file:
                        imagen.save(temp_file.name, quality=60)
                        temp_file.seek(0)
                
                    # Subir la imagen optimizada a Cloudinary
                        response = cloudinary.uploader.upload(temp_file.name, asset_folder='/dashboard_valero')

                        # Actualizar el campo de imagen con la URL de Cloudinary
                        imagen = Image(url=response['secure_url'])
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
            producto.delete()
            return DeleteProductoInfo(message="Producto eliminado con éxito")
        except ProductoInfo.DoesNotExist:
            return GraphQLError('Product not found')
        except:
            return GraphQLError("Something went wrong XC")    
        
class AddEntradaAlmacen(Mutation):
    class Arguments:
        metodo_pago = String(required=True)
        proveedor = String(required=True)
        variantes = GenericScalar(required=True)
        product_info = String(required=True)

    response = List(AddEntradaType)
    
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, metodo_pago, proveedor, variantes, product_info):
        producto_info = ProductoInfo.objects.get(codigo=product_info)

        entrada = EntradaAlmacen.objects.create(metodo_pago=metodo_pago, proveedor=proveedor,
                                                usuario=info.context.user)

        entrada.save()

        if type(variantes) != list:
            entrada.delete()
            raise GraphQLError("Formato corrupto: 'variante' debe ser <class: list> ")
        try:
            response = []
            for variante in variantes:
                color = variante['color']
                numeros = variante['numeros']
               
                productos_pa = []

                for num in numeros:
                    numero = num['numero']
                    cantidad = num['cantidad']
                  
                    ids = []
                    
                    i = 0
                    while i < cantidad:
                        i+=1
                        producto = Producto(
                            info=producto_info,
                            color=color,
                            numero=numero,
                            entrada=entrada
                        )

                        producto.save()
                        ids.append(producto.id)
                    
                    if len(ids) == 1:
                        array_ids = ids[0]
                    else:
                        array_ids = f'{ids[0]}-{ids[-1]}'

                    productos_pa.append({
                        "numero": numero,
                        "ids": array_ids
                    })

                response.append({
                    'color': color,
                    'numeros': productos_pa
                })
            entrada.productos = response
            entrada.save()
                        
        except Exception as e:
            entrada.delete()
            raise GraphQLError(type(e))

        return AddEntradaAlmacen(response)
    
        
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
            return GraphQLError('Entrada no encontrada')
        except:
            return GraphQLError("Something went wrong XC")
        
class AddVentas(Mutation):
    class Arguments:
        productos = List(ID, required=True)
        punto_venta = ID(required=True)
        metodo_pago = String(required=True)

    ventas = Field(VentasType)
    
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "VENDEDOR") 
    def mutate(self, info, productos, punto_venta, metodo_pago):
        if info.context.user.rol == "ADMIN" or info.context.user.punto_venta.id == int(punto_venta):
            
            productos = Producto.objects.filter(pk__in=productos)
            punto_venta = get_object_or_404(PuntoVenta, pk=punto_venta)

            ventas = Ventas.objects.create(punto_venta=punto_venta, metodo_pago=metodo_pago,
                                           usuario=info.context.user)
            ventas.save()

            ventas.productos.set(productos)
            productos.update(in_stock=False)
            return AddVentas(ventas)
        else:
            return GraphQLError("No tienes permisos para relizar esta acción")
        
    
class UpdateVentas(Mutation):
    class Arguments:
        id = ID(required=True)
        productos = List(ID, required=True)
        punto_venta = ID(required=True)
        metodo_pago = String(required=True)

    ventas = Field(VentasType)
    
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "VENDEDOR")
    def mutate(self, info, id, productos, punto_venta, metodo_pago):
        if info.context.user.rol == "ADMIN" or info.context.user.punto_venta.id == int(punto_venta):
            productos = Producto.objects.filter(pk__in=productos)
            ventas = get_object_or_404(Ventas, pk=id)
            punto_venta = get_object_or_404(PuntoVenta, pk=punto_venta)

            ventas.punto_venta = punto_venta
            ventas.usuario = info.context.user
            ventas.metodo_pago = metodo_pago
            ventas.productos.update(in_stock=True)
            ventas.save()

            ventas.productos.set(productos)
            productos.update(in_stock=False)
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
                if info.context.user.rol == "ADMIN" or info.context.user.punto_venta.id == ventas.punto_venta.id:
                    ventas.delete()
                    return DeleteVentas(message="Venta eliminada con éxito")
                return GraphQLError("No tienes permisos para relizar esta acción") 

            except Ventas.DoesNotExist:
                return GraphQLError('Venta no encontrada')
            except:
                return GraphQLError("Something went wrong XC")
        
       
class AddPuntoVenta(Mutation):
    class Arguments:
        nombre = String(required=True)

    punto_venta = Field(PuntoVentaType)
    
    @user_passes_test(lambda user: user.rol == "ADMIN")
    def mutate(self, info, nombre):
        punto_venta = PuntoVenta.objects.create(nombre=nombre)
        punto_venta.save()
        return AddPuntoVenta(punto_venta)
    
class UpdatePuntoVenta(Mutation):
    class Arguments:
        id = ID(required=True)
        nombre = String(required=True)

    punto_venta = Field(PuntoVentaType)
    
    @user_passes_test(lambda user: user.rol == "ADMIN")
    def mutate(self, info, id, nombre):
        
        punto_venta = get_object_or_404(PuntoVenta, pk=id)
        punto_venta.nombre = nombre
        punto_venta.save()

        return UpdatePuntoVenta(punto_venta)

class DeletePuntoVenta(Mutation):
    class Arguments:
        id = ID(required=True)

    message = String()

    @user_passes_test(lambda user: user.rol == "ADMIN")
    def mutate(self, info, id):
        try:
            punto_venta = get_object_or_404(PuntoVenta, pk=id)
            punto_venta.delete()
            return DeletePuntoVenta(message="Punto de venta eliminada con éxito")
        except EntradaAlmacen.DoesNotExist:
            return GraphQLError('Punto de venta no encontrada')
        except:
            return GraphQLError("Something went wrong XC")
        
class AddSalidaAlmacen(Mutation):
    class Arguments:
        productos = List(ID, required=True)
        punto_venta = ID(required=True)

    salida_almacen = Field(SalidaAlmacenType)
    
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, productos, punto_venta):
        
        productos = Producto.objects.filter(pk__in=productos)
        punto_venta = get_object_or_404(PuntoVenta, pk=punto_venta)
        usuario_search = get_object_or_404(User, pk=info.context.user.id)
        try:
            salida = SalidaAlmacen.objects.create(punto_venta=punto_venta, usuario=usuario_search)

            salida.productos.set(productos)
            productos.update(punto_venta=punto_venta)
                
            return AddSalidaAlmacen(salida_almacen=salida)
        except:
            return GraphQLError("Algo salió mal XC")
    
class UpdateSalidaAlmacen(Mutation):
    class Arguments:
        id = ID(required=True)
        productos = List(ID, required=True)
        punto_venta = ID(required=True)

    salida_almacen = Field(SalidaAlmacenType)
    
    @user_passes_test(lambda user: user.rol == "ADMIN" or user.rol == "ALMACENERO")
    def mutate(self, info, id, productos, punto_venta):
        
        productos = Producto.objects.filter(pk__in=productos)
        salida = get_object_or_404(SalidaAlmacen, pk=id)
        punto_venta = get_object_or_404(PuntoVenta, pk=punto_venta)
        usuario_search = get_object_or_404(User, pk=info.context.user.id)

        salida.punto_venta = punto_venta
        salida.usuario = info.context.user

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
            salida.productos.update(punto_venta=None)
            salida.delete()
            return DeleteSalidaAlmacen(message="Salida eliminada con éxito")
        except EntradaAlmacen.DoesNotExist:
            return GraphQLError('Salida no encontrada')
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
    # update_entrada = UpdateEntradaAlmacen.Field()
    delete_entrada = DeleteEntradaAlmacen.Field()
    add_salida = AddSalidaAlmacen.Field()
    update_salida = UpdateSalidaAlmacen.Field()
    delete_salida = DeleteSalidaAlmacen.Field()
    add_punto_venta = AddPuntoVenta.Field()
    update_punto_venta = UpdatePuntoVenta.Field()
    delete_punto_venta = DeletePuntoVenta.Field()
    add_venta = AddVentas.Field()
    update_venta = UpdateVentas.Field()
    delete_venta = DeleteVentas.Field()
    login = ObtainJSONWebToken.Field() 
