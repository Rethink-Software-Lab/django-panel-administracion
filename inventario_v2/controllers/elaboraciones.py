from datetime import datetime
from typing import List
from django.http import Http404
from ninja.errors import HttpError
from inventario.models import (
    User,
    Tarjetas,
    BalanceTarjetas,
    TransferenciasTarjetas,
    TipoTranferenciaChoices,
    Elaboraciones,
    ProductoInfo,
    Ingrediente_Cantidad,
)
from inventario_v2.utils import validate_transferencia
from ..schema import (
    TarjetasModifySchema,
    TarjetasEndpoint,
    TransferenciasTarjetasModify,
    ElaboracionesSchema,
    ElaboracionesEndpoint,
    ElaboracionesModifySchema,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin, isSupervisor
from django.db import transaction
from decimal import Decimal
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce, Round


@api_controller("elaboraciones/", tags=["Elaboraciones"], permissions=[isAdmin])
class ElaboracionesController:
    @route.get("", response=ElaboracionesEndpoint)
    def get_all_elaboraciones(self):
        elaboraciones = Elaboraciones.objects.all().order_by("-id")

        productos = ProductoInfo.objects.filter(categoria__nombre="Cafetería")

        return {"elaboraciones": elaboraciones, "productos": productos}

    @route.post("")
    def add_elaboracion(self, body: ElaboracionesModifySchema):
        body_dict = body.model_dump()

        for ingrediente in body_dict["ingredientes"]:
            producto = get_object_or_404(ProductoInfo, pk=ingrediente["producto"])

        with transaction.atomic():

            new_ingredientes = [
                Ingrediente_Cantidad(
                    id=producto.pk,
                    producto=producto.producto,
                    cantidad=producto.cantidad,
                )
                for producto in body_dict["ingredientes"]
            ]

            ingredientes = Ingrediente_Cantidad.objects.bulk_create(new_ingredientes)
            Elaboraciones.objects.create(
                ingredientes=ingredientes,
                nombre=body_dict["nombre"],
                precio=body_dict["precio"],
                mano_obra=body_dict["mano_obra"],
            )

        return

    @route.delete("{id}/")
    def delete_tarjeta(self, id: int):
        tarjeta = get_object_or_404(Tarjetas, pk=id)
        try:
            tarjeta.delete()
            return
        except Exception as e:
            raise HttpError(400, f"No se pudo eliminar la tarjeta: {e}")

    @route.post("add/transferencia/")
    def add_transferencia(self, request, body: TransferenciasTarjetasModify):
        body_dict = body.model_dump()

        try:
            cantidad = Decimal(body_dict["cantidad"])
        except:
            raise HttpError(400, "La cantidad debe ser un número decimal valido")

        if body_dict["tipo"] == TipoTranferenciaChoices.EGRESO:
            try:
                tarjeta = validate_transferencia(id_tarjeta=body_dict["tarjeta"])
            except Http404:
                raise HttpError(404, "Tarjeta no encontrada")
            except Exception as e:
                raise HttpError(400, f"{e}")
        else:
            tarjeta = get_object_or_404(Tarjetas, pk=body_dict["tarjeta"])

        usuario = get_object_or_404(User, pk=request.auth["id"])

        with transaction.atomic():
            balance = BalanceTarjetas.objects.get(tarjeta=tarjeta)
            if body_dict["tipo"] == TipoTranferenciaChoices.INGRESO:
                balance.valor = balance.valor + cantidad
                balance.save()
            elif body_dict["tipo"] == TipoTranferenciaChoices.EGRESO:
                if (balance.valor - cantidad) <= 0:
                    raise HttpError(400, "No hay saldo sufiente para esta accion")

                balance.valor = balance.valor - cantidad
                balance.save()

            TransferenciasTarjetas.objects.create(
                tarjeta=tarjeta,
                cantidad=cantidad,
                descripcion=body_dict["descripcion"],
                tipo=body_dict["tipo"],
                usuario=usuario,
            )

    @route.delete("transferencia/{id}/")
    def delete_transferencia(self, id: int):
        transferencia = get_object_or_404(TransferenciasTarjetas, pk=id)

        if transferencia.tipo == TipoTranferenciaChoices.INGRESO:
            with transaction.atomic():
                balance = BalanceTarjetas.objects.get(tarjeta=transferencia.tarjeta)
                if (balance.valor - transferencia.cantidad) >= 0:
                    balance.valor = balance.valor - transferencia.cantidad
                    balance.save()
                else:
                    raise HttpError(400, "No hay saldo sufiente para esta acción")

                transferencia.delete()

        elif transferencia.tipo == TipoTranferenciaChoices.EGRESO:
            with transaction.atomic():
                balance = BalanceTarjetas.objects.get(tarjeta=transferencia.tarjeta)
                balance.valor = balance.valor + transferencia.cantidad
                balance.save()

                transferencia.delete()

        return
