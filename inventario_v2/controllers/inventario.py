from ninja.errors import HttpError
from inventario.models import ProductoInfo, Producto
from ..schema import InventarioAlmacenSchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db.models import F, Count, Q
from typing import List



from django.db import transaction

from ..custom_permissions import isAuthenticated


@api_controller("inventario/", tags=["Inventario"], permissions=[isAuthenticated])
class InventarioController:

    @route.get("almacen/", response=InventarioAlmacenSchema)
    def getInventarioAlmacen(self):
        producto_info = ProductoInfo.objects.filter(
        producto__venta__isnull=True,
        producto__area_venta__isnull=True,
        ).annotate(cantidad=Count(F('producto'))
        ).exclude(Q(cantidad__lt=1) | Q(categoria__nombre='Zapatos')
        ).values("id", "descripcion", "codigo" , "cantidad", "categoria__nombre")
        print(producto_info)
        zapatos = Producto.objects.filter(
            venta__isnull=True, 
            area_venta__isnull=True,
            info__categoria__nombre="Zapatos"
            )
            
        return { "productos": producto_info, "zapatos": zapatos }
        
       

    
    