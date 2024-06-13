from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Image)
admin.site.register(Producto)
admin.site.register(EntradaAlmacen)
admin.site.register(SalidaAlmacen)
admin.site.register(PuntoVenta)
admin.site.register(Ventas)

@admin.register(ProductoInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ["id", "codigo", "descripcion", "imagen", "precio_costo", "precio_venta"]
