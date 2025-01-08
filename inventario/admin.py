from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Image)
admin.site.register(Producto)
admin.site.register(EntradaAlmacen)
admin.site.register(SalidaAlmacen)
admin.site.register(AreaVenta)
admin.site.register(Ventas)
admin.site.register(Categorias)
admin.site.register(Tarjetas)
admin.site.register(BalanceTarjetas)
admin.site.register(TransferenciasTarjetas)
admin.site.register(Productos_Cafeteria)
admin.site.register(Inventario_Producto_Cafeteria)
admin.site.register(Entradas_Cafeteria)
admin.site.register(Productos_Entradas_Cafeteria)
admin.site.register(Ingrediente_Cantidad)
admin.site.register(Elaboraciones)
admin.site.register(Ventas_Cafeteria)


@admin.register(ProductoInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "codigo",
        "descripcion",
        "imagen",
        "categoria",
        "precio_costo",
        "precio_venta",
        "pago_trabajador",
    ]


@admin.register(Transferencia)
class TransferenciaAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "usuario",
        "de",
        "para",
        "created_at",
        "mostrar_productos",
    ]

    def mostrar_productos(self, obj):
        return ", ".join([str(producto) for producto in obj.productos.all()])

    mostrar_productos.short_description = "Productos"
