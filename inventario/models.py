from decimal import Decimal
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


class BancoChoices(models.TextChoices):
    BPA = "BPA", "BPA"
    BANDEC = "BANDEC", "Bandec"


class CuentasChoices(models.TextChoices):
    EFECTIVO = "EFECTIVO", "Efectivo"
    BANCARIA = "BANCARIA", "Bancaria"


class MonedaChoices(models.TextChoices):
    CUP = "CUP", "CUP"
    USD = "USD", "USD"


class Cuentas(models.Model):
    nombre = models.CharField(max_length=50, blank=False, null=False)
    tipo = models.CharField(
        max_length=30, choices=CuentasChoices.choices, blank=False, null=False
    )
    saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=False,
        null=False,
    )
    moneda = models.CharField(
        max_length=3,
        choices=MonedaChoices.choices,
        blank=False,
        null=False,
        default=MonedaChoices.CUP,
    )
    banco = models.CharField(
        max_length=50, choices=BancoChoices.choices, blank=True, null=True
    )


class AreaVenta(models.Model):
    nombre = models.CharField(max_length=50, blank=False, null=False)
    color = models.CharField(max_length=10)
    active = models.BooleanField(default=True, null=False, blank=False)
    cuenta = models.ForeignKey(
        Cuentas, on_delete=models.DO_NOTHING, null=False, blank=False
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Área de Venta"
        verbose_name_plural = "Áreas de Venta"


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
    VENDEDOR_CAFETERIA = "VENDEDOR CAFETERÍA", "Vendedor Cafetería"
    SUPERVISOR = "SUPERVISOR", "Supervisor"


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
    descripcion = models.CharField(max_length=100, blank=False, null=False)
    imagen = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True)
    pago_trabajador = models.IntegerField()
    categoria = models.ForeignKey(Categorias, on_delete=models.CASCADE)

    @property
    def precio_costo(self):
        return self.historial_costo.order_by("-id").first().precio

    @property
    def precio_venta(self):
        return self.historial_venta.order_by("-id").first().precio

    def __str__(self):
        return self.descripcion


class HistorialPrecioCostoSalon(models.Model):
    producto_info = models.ForeignKey(
        ProductoInfo,
        on_delete=models.CASCADE,
        related_name="historial_costo",
        null=True,
    )
    precio = models.DecimalField(
        max_digits=7, decimal_places=2, blank=False, null=False
    )
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)


class HistorialPrecioVentaSalon(models.Model):
    producto_info = models.ForeignKey(
        ProductoInfo,
        on_delete=models.CASCADE,
        related_name="historial_venta",
        null=True,
    )
    precio = models.DecimalField(
        max_digits=7, decimal_places=2, blank=False, null=False
    )
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)


class Proveedor(models.Model):
    nombre = models.CharField(max_length=100, blank=False, null=False)
    direccion = models.CharField(max_length=100, blank=False, null=False)
    nit = models.CharField(max_length=30, blank=False, null=False)
    no_cuenta_cup = models.CharField(max_length=30, blank=True, null=True)
    no_cuenta_mayorista = models.CharField(max_length=30, blank=True, null=True)
    telefono = models.CharField(max_length=10, blank=False, null=False)


class METODO_PAGO(models.TextChoices):
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
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True)
    comprador = models.CharField(max_length=30, blank=False, null=False)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.created_at.strftime('%d/%m/%Y - %H:%M')}"

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
    DIARIO = "DIARIO", "Diario"
    SEMANAL = "SEMANAL", "Semanal"
    MENSUAL = "MENSUAL", "Mensual"
    LUNES_SABADO = "LUNES_SABADO", "Lunes-Sábado"


class Gastos(models.Model):
    tipo = models.CharField(
        max_length=30, choices=GastosChoices.choices, blank=False, null=False
    )
    areas_venta = models.ManyToManyField(AreaVenta, blank=True)
    cuenta = models.ForeignKey(Cuentas, on_delete=models.CASCADE, null=True)
    is_cafeteria = models.BooleanField(default=False)
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


# CAFERTERIA
class Productos_Cafeteria(models.Model):
    nombre = models.CharField(max_length=50, blank=False, null=False)

    @property
    def precio_costo(self):
        ultimo_costo = self.historial_costo.order_by("-id").first()
        return ultimo_costo.precio if ultimo_costo else Decimal("0.00")

    @property
    def precio_venta(self):
        ultima_venta = self.historial_venta.order_by("-id").first()
        return ultima_venta.precio if ultima_venta else Decimal("0.00")

    def __str__(self) -> str:
        return self.nombre


class HistorialPrecioCostoCafeteria(models.Model):
    producto = models.ForeignKey(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        related_name="historial_costo",
        null=True,
    )
    precio = models.DecimalField(
        max_digits=20, decimal_places=10, blank=False, null=False
    )
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)


class HistorialPrecioVentaCafeteria(models.Model):
    producto = models.ForeignKey(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        related_name="historial_venta",
        null=True,
    )
    precio = models.DecimalField(
        max_digits=20, decimal_places=10, blank=False, null=False
    )
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)


class Inventario_Almacen_Cafeteria(models.Model):
    producto = models.OneToOneField(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="inventario_almacen",
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )

    class Meta:
        verbose_name = "Inventario Almacén Cafetería"
        verbose_name_plural = "Inventario Almacén Cafetería"


class Inventario_Area_Cafeteria(models.Model):
    producto = models.OneToOneField(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="inventario_area",
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )

    class Meta:
        verbose_name = "Inventario Area Cafetería"
        verbose_name_plural = "Inventario Area Cafetería"


class Ingrediente_Cantidad(models.Model):
    ingrediente = models.ForeignKey(
        Productos_Cafeteria, on_delete=models.CASCADE, null=False, blank=False
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=3, blank=False, null=False
    )


class Elaboraciones(models.Model):
    nombre = models.CharField(max_length=50, blank=False, null=False)
    ingredientes_cantidad = models.ManyToManyField(Ingrediente_Cantidad, blank=False)
    mano_obra = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )

    @property
    def precio(self):
        ultimo_precio = self.precio_elaboracion.order_by("-id").first()
        return ultimo_precio.precio if ultimo_precio else Decimal("0.00")


class PrecioElaboracion(models.Model):
    elaboracion = models.ForeignKey(
        Elaboraciones,
        on_delete=models.CASCADE,
        related_name="precio_elaboracion",
        null=True,
    )
    precio = models.DecimalField(
        max_digits=7, decimal_places=2, blank=False, null=False
    )
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)


class Productos_Entradas_Cafeteria(models.Model):
    producto = models.ForeignKey(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )


class Entradas_Cafeteria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    productos = models.ManyToManyField(Productos_Entradas_Cafeteria, blank=False)
    metodo_pago = models.CharField(
        max_length=30, choices=METODO_PAGO.choices, blank=False, null=False
    )
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True)
    proveedor_nombre = models.CharField(max_length=100, blank=True, null=True)
    proveedor_nit = models.CharField(max_length=30, blank=True, null=True)
    proveedor_telefono = models.CharField(max_length=10, blank=True, null=True)
    proveedor_direccion = models.CharField(max_length=100, blank=True, null=True)
    proveedor_no_cuenta_cup = models.CharField(max_length=30, blank=True, null=True)
    proveedor_no_cuenta_mayorista = models.CharField(
        max_length=30, blank=True, null=True
    )
    comprador = models.CharField(max_length=30, blank=False, null=False)


class Productos_Salidas_Cafeteria(models.Model):
    producto = models.ForeignKey(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )


class Elaboraciones_Salidas_Almacen_Cafeteria(models.Model):
    producto = models.ForeignKey(
        Elaboraciones,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )


class Salidas_Cafeteria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    productos = models.ManyToManyField(Productos_Salidas_Cafeteria, blank=True)
    elaboraciones = models.ManyToManyField(
        Elaboraciones_Salidas_Almacen_Cafeteria, blank=True
    )


class Productos_Ventas_Cafeteria(models.Model):
    # Cantidad de cada producto de una venta de la cafeteria
    producto = models.ForeignKey(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.DecimalField(max_digits=7, decimal_places=2, null=True)


class Elaboraciones_Ventas_Cafeteria(models.Model):
    # Cantidad de cada elaboraciones de una venta de la cafeteria
    producto = models.ForeignKey(
        Elaboraciones,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.IntegerField(null=False, blank=False)


class Ventas_Cafeteria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    productos = models.ManyToManyField(Productos_Ventas_Cafeteria, blank=False)
    elaboraciones = models.ManyToManyField(Elaboraciones_Ventas_Cafeteria, blank=False)
    metodo_pago = models.CharField(
        max_length=30, choices=METODO_PAGO.choices, blank=False, null=False
    )
    efectivo = models.DecimalField(max_digits=7, decimal_places=2, null=True)
    transferencia = models.DecimalField(max_digits=7, decimal_places=2, null=True)


class Productos_Cantidad_Cuenta_Casa(models.Model):
    producto = models.ForeignKey(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )


class Elaboraciones_Cantidad_Cuenta_Casa(models.Model):
    producto = models.ForeignKey(
        Elaboraciones,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )


class CuentaCasa(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    productos = models.ManyToManyField(Productos_Cantidad_Cuenta_Casa, blank=True)
    elaboraciones = models.ManyToManyField(
        Elaboraciones_Cantidad_Cuenta_Casa, blank=True
    )
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_almacen = models.BooleanField(default=False)

    def __str__(self):
        return self.created_at.strftime("%d/%m/%Y - %H:%M")


class TipoTranferenciaChoices(models.TextChoices):
    INGRESO = "INGRESO", "Ingreso"
    EGRESO = "EGRESO", "Egreso"
    VENTA = "VENTA", "Venta"
    PAGO_TRABAJADOR = "PAGO_TRABAJADOR", "Pago trabajador"
    GASTO_FIJO = "GASTO_FIJO", "Gasto fijo"
    GASTO_VARIABLE = "GASTO_VARIABLE", "Gasto variable"
    TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
    ENTRADA = "ENTRADA", "Entrada"


class Transacciones(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )
    moneda = models.CharField(
        max_length=3,
        choices=MonedaChoices.choices,
        blank=False,
        null=False,
        default=MonedaChoices.CUP,
    )
    descripcion = models.CharField(max_length=100, blank=False, null=False)
    cuenta = models.ForeignKey(
        Cuentas,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tipo = models.CharField(
        max_length=30,
        choices=TipoTranferenciaChoices.choices,
        blank=False,
        null=False,
    )
    venta = models.ForeignKey(Ventas, on_delete=models.CASCADE, null=True, blank=True)
    venta_cafeteria = models.ForeignKey(
        Ventas_Cafeteria, on_delete=models.CASCADE, null=True, blank=True
    )
    entrada = models.ForeignKey(
        EntradaAlmacen, on_delete=models.CASCADE, null=True, blank=True
    )
    entrada_cafeteria = models.ForeignKey(
        Entradas_Cafeteria, on_delete=models.CASCADE, null=True, blank=True
    )
    gasto = models.ForeignKey(Gastos, on_delete=models.CASCADE, null=True, blank=True)
    cuenta_casa = models.ForeignKey(
        CuentaCasa, on_delete=models.CASCADE, null=True, blank=True
    )


class Productos_Cantidad_Merma(models.Model):
    producto = models.ForeignKey(
        Productos_Cafeteria,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )


class Elaboraciones_Cantidad_Merma(models.Model):
    producto = models.ForeignKey(
        Elaboraciones,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2, blank=False, null=False
    )


class MermaCafeteria(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    productos = models.ManyToManyField(Productos_Cantidad_Merma, blank=True)
    elaboraciones = models.ManyToManyField(Elaboraciones_Cantidad_Merma, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_almacen = models.BooleanField(default=False)

    def __str__(self):
        return self.created_at.strftime("%d/%m/%Y - %H:%M")

    class Meta:
        verbose_name = "Merma"
        verbose_name_plural = "Merma"


class VendedorExterno(models.Model):
    nombre = models.CharField(max_length=50, blank=False, null=False)
    telefono = models.CharField(max_length=50, blank=False, null=False)
    codigo_referido = models.CharField(unique=True, max_length=8)

    def __str__(self):
        return self.nombre
