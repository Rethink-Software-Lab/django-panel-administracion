from django.urls import path
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
from inventario.schema import schema
from graphene_file_upload.django import FileUploadGraphQLView

urlpatterns = [
    path('api', csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True, schema=schema)))
]