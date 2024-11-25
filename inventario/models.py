from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


class AreaVenta(models.Model):
    nombre = models.CharField(max_length=50, blank=False, null=False)
    color = models.CharField(max_length=10)


class UserManager(BaseUserManager):
    # Manager para Perfiles de Usuario

    def create_user(self, username, password=None, **extra_fields):
        # Crear Nuevo User Profile
        if not username:
            raise ValueError("Usuario requerido")

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


class RolesChoices(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    ALMACENERO = "ALMACENERO", "Almacenero"
    VENDEDOR = "VENDEDOR", "Vendedor"


class AlmacenChoices(models.TextChoices):
    PRINCIPAL = "PRINCIPAL", "Principal"
    CAFETERIA = "CAFETERIA", "Cafetería"
    REVOLTOSA = "REVOLTOSA", "Revoltosa"


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=15, unique=True)
    rol = models.CharField(
        max_length=30, choices=RolesChoices.choices, blank=False, null=False
    )
    area_venta = models.ForeignKey(
        AreaVenta, on_delete=models.SET_NULL, null=True, blank=True
    )
    almacen = models.CharField(
        max_length=30, choices=AlmacenChoices.choices, blank=True, null=True
    )
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "username"

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"


class Image(models.Model):
    public_id = models.CharField(max_length=50, unique=True)
    url = models.URLField(unique=True)


class Categorias(models.Model):
    nombre = models.CharField(max_length=50)


class ProductoInfo(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    descripcion = models.CharField(max_length=100, blank=False, null=False)
    imagen = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True)
    pago_trabajador = models.IntegerField()
    categoria = models.ForeignKey(Categorias, on_delete=models.CASCADE)
    precio_costo = models.DecimalField(
        max_digits=7, decimal_places=2, blank=False, null=False
    )
    precio_venta = models.DecimalField(
        max_digits=7, decimal_places=2, blank=False, null=False
    )


class METODO_PAGO(models.TextChoices):
    FIJO = "FIJO", "Fijo"
    EFECTIVO = (
        "EFECTIVO",
        "Efectivo",
    )
    TRANSFERENCIA = (
        "TRANSFERENCIA",
        "Transferencia",
    )
    MIXTO = (
        "MIXTO",
        "Mixto",
    )


class EntradaAlmacen(models.Model):
    metodo_pago = models.CharField(
        max_length=30, choices=METODO_PAGO.choices, blank=False, null=False
    )
    proveedor = models.CharField(max_length=30, blank=False, null=False)
    comprador = models.CharField(max_length=30, blank=False, null=False)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.created_at}"

    class Meta:
        verbose_name = "EntradaAlmacen"
        verbose_name_plural = "EntradasAlmacen"


class Ventas(models.Model):
    area_venta = models.ForeignKey(AreaVenta, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    metodo_pago = models.CharField(
        max_length=30, choices=METODO_PAGO.choices, blank=False, null=False
    )
    efectivo = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    transferencia = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SalidaAlmacen(models.Model):
    area_venta = models.ForeignKey(AreaVenta, on_delete=models.CASCADE, null=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SalidaAlmacenRevoltosa(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Producto(models.Model):
    info = models.ForeignKey(ProductoInfo, on_delete=models.CASCADE)
    color = models.CharField(max_length=100, blank=True, null=True)
    numero = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    entrada = models.ForeignKey(EntradaAlmacen, on_delete=models.CASCADE, null=True)
    salida = models.ForeignKey(SalidaAlmacen, on_delete=models.SET_NULL, null=True)
    salida_revoltosa = models.ForeignKey(
        SalidaAlmacenRevoltosa, on_delete=models.SET_NULL, null=True
    )
    venta = models.ForeignKey(Ventas, on_delete=models.SET_NULL, null=True)
    area_venta = models.ForeignKey(AreaVenta, on_delete=models.SET_NULL, null=True)
    almacen_revoltosa = models.BooleanField(default=False)
    almacen_cafeteria = models.BooleanField(default=False)


class SalidaAlmacenCafeteria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    info_producto = models.ForeignKey(ProductoInfo, on_delete=models.CASCADE)
    cantidad = models.IntegerField(null=False, blank=False)


class EntradaAlmacenCafeteria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    info_producto = models.ForeignKey(ProductoInfo, on_delete=models.CASCADE)
    metodo_pago = models.CharField(
        max_length=30, choices=METODO_PAGO.choices, blank=False, null=False
    )
    cantidad = models.IntegerField(null=False, blank=False)
    proveedor = models.CharField(max_length=30, blank=False, null=False)
    comprador = models.CharField(max_length=30, blank=False, null=False)


class Transferencia(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    productos = models.ManyToManyField(Producto, blank=False)
    de = models.ForeignKey(
        AreaVenta, on_delete=models.SET_NULL, null=True, related_name="area_remitente"
    )
    para = models.ForeignKey(
        AreaVenta, on_delete=models.SET_NULL, null=True, related_name="area_destino"
    )

    def __str__(self):
        return f"{self.created_at}"

    class Meta:
        verbose_name = "Transferencia"
        verbose_name_plural = "Transferencias"


class AjusteInventario(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    productos = models.ManyToManyField(Producto, blank=False)
    motivo = models.CharField(max_length=100, null=False)
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="ajuste"
    )


class GastosChoices(models.TextChoices):
    FIJO = "FIJO", "Fijo"
    VARIABLE = "VARIABLE", "Variable"


class FrecuenciaChoices(models.TextChoices):
    LUNES_SABADO = "LUNES_SABADO", "Lunes-Sábado"
    SEMANAL = "SEMANAL", "Semanal"
    MENSUAL = "MENSUAL", "Mensual"


class Gastos(models.Model):
    tipo = models.CharField(
        max_length=30, choices=GastosChoices.choices, blank=False, null=False
    )
    area_venta = models.ForeignKey(AreaVenta, on_delete=models.CASCADE, null=False)
    descripcion = models.CharField(max_length=100, blank=False, null=False)
    cantidad = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    # Fijos
    frecuencia = models.CharField(
        max_length=30, choices=FrecuenciaChoices.choices, blank=True, null=True
    )
    # mensuales
    dia_mes = models.IntegerField(null=True, blank=True)
    # semanales
    dia_semana = models.IntegerField(null=True, blank=True)
