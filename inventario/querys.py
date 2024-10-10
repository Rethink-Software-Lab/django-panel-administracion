from graphene import ObjectType, Field
from .types import *
from .models import *
from graphql_jwt.decorators import login_required


from django.core.paginator import Paginator


class Query(ObjectType):
    all_area_venta = Field(AreaVentaFilterType, page=Int(required=False))

    @login_required
    def resolve_all_area_venta(self, info, page=None):
        if page is None:
            areas_venta = AreaVenta.objects.all().order_by("-id")
            return AreaVentaFilterType(areas_venta)
        p = Paginator(AreaVenta.objects.all().order_by("-id"), 20)
        areas_venta = p.get_page(page)
        return AreaVentaFilterType(
            areas_venta, info=InfoType(page=page, total_pages=p.num_pages)
        )
