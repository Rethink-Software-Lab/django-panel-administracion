from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from inventario_v2.api import app

urlpatterns = [
    path("admin/", admin.site.urls),
    path("v2/", app.urls),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "Panel de Administración - Valero"
admin.site.site_title = "Inicio"
admin.site.index_title = "Panel de Administración"
