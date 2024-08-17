from ninja.errors import HttpError
from inventario.models import ProductoInfo, SalidaAlmacen, Producto, User, AreaVenta
from ..schema import AddSalidaSchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404

from django.db import transaction

from ..custom_permissions import isStaff


@api_controller("salidas/", tags=["Salidas"], permissions=[isStaff])
class SalidasController:

    @route.post("")
    def addSalida(self, request, data: AddSalidaSchema):
        dataDict = data.model_dump()
        
        area_venta = get_object_or_404(AreaVenta, pk=dataDict['areaVenta'])
        producto_info = get_object_or_404(ProductoInfo, codigo=dataDict['producto_info'])
        usuario_search = get_object_or_404(User, pk=request.auth["id"])
        
        if producto_info.categoria.nombre == "Zapatos":
            
            ids_unicos = list(dict.fromkeys(dataDict['zapatos_id']))
            
            ids_count = Producto.objects.filter(id__in=ids_unicos).count()

            if ids_count < len(ids_unicos):
                raise HttpError(400, "Algunos ids no existen")
            
            filtro1 = Producto.objects.filter(pk__in=ids_unicos, info=producto_info)
            
            if filtro1.count() < len(ids_unicos):
                raise HttpError(400, "Los ids deben ser de un único producto")
            
            filtro2 = filtro1.filter(venta__isnull=True)
            
            if filtro2.count() < len(ids_unicos):
                raise HttpError(400, "Algunos productos ya han sido vendidos.")
            
            productos = filtro2.filter(area_venta__isnull=True)
            
            if productos.count() < len(ids_unicos):
                raise HttpError(400, "Algunos productos no están en el almacén.")
            
            
            try:
                with transaction.atomic():
                    salida = SalidaAlmacen.objects.create(
                        area_venta=area_venta, usuario=usuario_search
                    )

                    salida.productos.set(productos)
                    productos.update(area_venta=area_venta)

                    return {"success": True}
            except:
                raise HttpError(500, "Algo salió mal al agregar la salida.")
            
        elif dataDict['cantidad'] and dataDict['cantidad'] > 0:
           
                with transaction.atomic():
                    cantidad = dataDict['cantidad']
                    salida = SalidaAlmacen.objects.create(
                        area_venta=area_venta, usuario=usuario_search
                    )

                    productos = Producto.objects.filter(area_venta__isnull=True, venta__isnull=True, info=producto_info)[:cantidad]
                    
                    if productos.count() < cantidad:
                        raise HttpError(400, f"No hay {producto_info.descripcion} suficientes para esta accion")
                             
                    salida.productos.set(productos)
                    for producto in productos:
                        producto.area_venta = area_venta
                        producto.save()
                        
                    return {"success": True}
            
        
        else:
            raise HttpError(400, "Cantidad requerida en productos != Zapatos")    
        
        

    @route.delete("{id}/")
    def deleteSalida(self, id: int):
        salida = get_object_or_404(SalidaAlmacen, pk=id)
        try:
            salida.delete()
            return {"success": True}
        except:
            raise HttpError(500, "Error inesperado.")
   
        
