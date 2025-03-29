from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Image)
admin.site.register(EntradaAlmacen)
admin.site.register(SalidaAlmacen)
admin.site.register(Ventas)
admin.site.register(Categorias)
admin.site.register(Cuentas)
admin.site.register(TransferenciasTarjetas)
admin.site.register(Productos_Cafeteria)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "color",
        "numero",
        "area_venta",
        "info_producto",
        "entrada_adapt",
        "salida_adapt",
        "salida_revoltosa_adapt",
        "venta_adapt",
        "almacen_revoltosa",
    ]
    search_fields = ["info__descripcion", "info__codigo"]
    list_filter = ["area_venta"]

    def info_producto(self, obj):
        return f"{obj.info.descripcion} - {obj.info.codigo}"

    def entrada_adapt(self, obj):
        return (
            obj.entrada.created_at.strftime("%d/%m/%Y - %H:%M") if obj.entrada else None
        )

    def salida_adapt(self, obj):
        return (
            obj.salida.created_at.strftime("%d/%m/%Y - %H:%M") if obj.salida else None
        )

    def salida_revoltosa_adapt(self, obj):
        return (
            obj.salida_revoltosa.created_at.strftime("%d/%m/%Y - %H:%M")
            if obj.salida_revoltosa
            else None
        )

    def venta_adapt(self, obj):
        return obj.venta.created_at.strftime("%d/%m/%Y - %H:%M") if obj.venta else None

    info_producto.short_description = "Info"
    entrada_adapt.short_description = "Entrada"
    salida_adapt.short_description = "Salida"
    salida_revoltosa_adapt.short_description = "Salida Revoltosa"
    venta_adapt.short_description = "Venta"


@admin.register(AreaVenta)
class AreaVentaAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "nombre",
        "color",
    ]


@admin.register(MermaCafeteria)
class MermaAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "created_at_adapt",
        "productos_adapt",
        "elaboraciones_adapt",
        "usuario",
        "is_almacen",
    ]

    def created_at_adapt(self, obj):
        return obj.created_at.strftime("%d/%m/%Y - %H:%M")

    def productos_adapt(self, obj):
        return obj.productos.all().count()

    def elaboraciones_adapt(self, obj):
        return obj.elaboraciones.all().count()

    created_at_adapt.short_description = "Fecha"
    productos_adapt.short_description = "Productos"
    elaboraciones_adapt.short_description = "Elaboraciones"


@admin.register(Inventario_Area_Cafeteria)
class InventarioAreaCafeteriaAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "producto_nombre",
        "cantidad",
    ]
    search_fields = ["producto__nombre"]
    list_editable = ["cantidad"]

    def producto_nombre(self, obj):
        return obj.producto.nombre

    producto_nombre.short_description = "Producto"


@admin.register(Inventario_Almacen_Cafeteria)
class InventarioAlmacenCafeteriaAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "producto_nombre",
        "cantidad",
    ]
    search_fields = ["producto__nombre"]
    list_editable = ["cantidad"]

    def producto_nombre(self, obj):
        return obj.producto.nombre

    producto_nombre.short_description = "Producto"


admin.site.register(Entradas_Cafeteria)
admin.site.register(Productos_Entradas_Cafeteria)
admin.site.register(Ingrediente_Cantidad)
admin.site.register(Elaboraciones)
admin.site.register(Ventas_Cafeteria)
admin.site.register(Salidas_Cafeteria)


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
