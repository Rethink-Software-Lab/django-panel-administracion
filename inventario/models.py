from django.db import models
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import cloudinary.uploader 
from PIL import Image as IMG
import tempfile


class PuntoVenta(models.Model):
    nombre = models.CharField(max_length=50, blank=False, null=False)

class UserManager(BaseUserManager):
    # Manager para Perfiles de Usuario

    def create_user(self, username, password = None, **extra_fields):
        # Crear Nuevo User Profile
        if not username:
            raise ValueError('Usuario requerido')

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user

    def create_superuser(self, username, password):
        user = self.create_user(username, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user

ROLES = (
   ("ADMIN", "Admin"),
   ("ALMACENERO", "Almacenero"),
   ("VENDEDOR", "Vendedor")
)

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=15, unique=True)
    rol = models.CharField(max_length=30, choices=ROLES, blank=False, null=False)
    punto_venta = models.ForeignKey(PuntoVenta, on_delete=models.SET_NULL, null=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'


class Image(models.Model):
    url = CloudinaryField("image", format="WebP", folder='dashboard_valero/')


class ProductoInfo(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=100, blank=False, null=False)
    imagen = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True)
    precio_costo = models.DecimalField(max_digits=7, decimal_places=2, blank=False, null=False)
    precio_venta = models.DecimalField(max_digits=7, decimal_places=2, blank=False, null=False)


METODO_PAGO = (
   ("EFECTIVO", "Efectivo"),
   ("TRANSFERENCIA", "Transferencia"),
)

class EntradaAlmacen(models.Model):
    metodo_pago = models.CharField(max_length=30, choices=METODO_PAGO, blank=False, null=False)
    proveedor = models.CharField(max_length=30, blank=False, null=False)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    productos = models.JSONField(default=dict, blank=False, null=False)

    def __str__(self):
        return f"{self.created_at}"

    class Meta:
        verbose_name = 'EntradaAlmacen'
        verbose_name_plural = 'EntradasAlmacen'

class Producto(models.Model):
    info = models.ForeignKey(ProductoInfo, on_delete=models.CASCADE)
    color = models.CharField(max_length=100)
    numero = models.DecimalField(max_digits=3, decimal_places=1)
    entrada = models.ForeignKey(EntradaAlmacen, on_delete=models.CASCADE)
    punto_venta = models.ForeignKey(PuntoVenta, on_delete=models.SET_NULL, null=True)
    in_stock = models.BooleanField(default=True)


class SalidaAlmacen(models.Model):
    productos = models.ManyToManyField(Producto)
    punto_venta = models.ForeignKey(PuntoVenta, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Ventas(models.Model):
    productos = models.ManyToManyField(Producto)   
    punto_venta = models.ForeignKey(PuntoVenta, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    metodo_pago = models.CharField(max_length=30, choices=METODO_PAGO, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

