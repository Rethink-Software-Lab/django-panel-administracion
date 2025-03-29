from ninja.errors import HttpError
from inventario.models import (
    User,
    Cuentas,
    TransferenciasTarjetas,
    TipoTranferenciaChoices,
)
from ..schema import (
    TarjetasModifySchema,
    TarjetasEndpoint,
    TransferenciasTarjetasModify,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin, isSupervisor
from django.db import transaction
from django.db.models import Sum, Q, Value
from django.db.models.functions import Round, Coalesce
from datetime import datetime
from decimal import Decimal


@api_controller("tarjetas/", tags=["Tarjetas"], permissions=[isAdmin | isSupervisor])
class TarjetasController:
    @route.get("", response=TarjetasEndpoint)
    def get_all_tarjetas(self):
        tarjetas = (
            Cuentas.objects.annotate(
                total_transferencias_mes=Round(
                    Coalesce(
                        Sum(
                            "transferenciastarjetas__cantidad",
                            filter=Q(
                                transferenciastarjetas__created_at__month=datetime.now().month,
                                transferenciastarjetas__tipo=TipoTranferenciaChoices.INGRESO,
                            ),
                        ),
                        Value(Decimal(0)),
                    ),
                    2,
                )
            )
            .all()
            .order_by("-id")
        )

        total_balance = tarjetas.aggregate(balance=Sum("saldo"))["balance"] or 0

        transferencias = TransferenciasTarjetas.objects.all().order_by("-id")
        return {
            "tarjetas": tarjetas,
            "transferencias": transferencias,
            "total_balance": total_balance,
        }

    @route.post("")
    def add_tarjeta(self, body: TarjetasModifySchema):
        body_dict = body.model_dump()

        tarjeta = Cuentas.objects.create(
            nombre=body_dict["nombre"],
            banco=body_dict["banco"],
        )

        try:
            saldo = Decimal(body_dict["saldo_inicial"])
        except:
            raise HttpError(400, "El saldo debe ser un número decimal valido")

        return

    @route.delete("{id}/")
    def delete_tarjeta(self, id: int):
        tarjeta = get_object_or_404(Cuentas, pk=id)
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

        tarjeta = get_object_or_404(Cuentas, pk=body_dict["cuenta"])

        usuario = get_object_or_404(User, pk=request.auth["id"])

        with transaction.atomic():
            if body_dict["tipo"] == TipoTranferenciaChoices.INGRESO:
                tarjeta.saldo += cantidad
                tarjeta.save()
            elif body_dict["tipo"] == TipoTranferenciaChoices.EGRESO:
                if (tarjeta.saldo - cantidad) <= 0:
                    raise HttpError(400, "No hay saldo sufiente para esta accion")

                tarjeta.saldo -= cantidad
                tarjeta.save()

            TransferenciasTarjetas.objects.create(
                cuenta=tarjeta,
                cantidad=cantidad,
                descripcion=body_dict["descripcion"],
                tipo=body_dict["tipo"],
                usuario=usuario,
            )

    @route.delete("transferencia/{id}/")
    def delete_transferencia(self, id: int):
        transferencia = get_object_or_404(TransferenciasTarjetas, pk=id)
        tarjeta = get_object_or_404(Cuentas, pk=transferencia.cuenta.pk)

        if transferencia.tipo == TipoTranferenciaChoices.INGRESO:
            with transaction.atomic():
                if (tarjeta.saldo - transferencia.cantidad) >= 0:
                    tarjeta.saldo -= transferencia.cantidad
                    tarjeta.save()
                else:
                    raise HttpError(400, "No hay saldo sufiente para esta acción")

                transferencia.delete()

        elif transferencia.tipo == TipoTranferenciaChoices.EGRESO:
            with transaction.atomic():
                tarjeta.saldo += transferencia.cantidad
                tarjeta.save()

                transferencia.delete()

        return
