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
