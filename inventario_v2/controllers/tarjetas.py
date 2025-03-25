from ninja.errors import HttpError
from inventario.models import (
    User,
    Cuentas,
    BalanceTarjetas,
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
            Cuentas.objects.select_related("balance")
            .annotate(
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

        total_balance = (
            BalanceTarjetas.objects.all().aggregate(balance=Sum("valor"))["balance"]
            or 0
        )

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

        if saldo > 0:
            BalanceTarjetas.objects.create(
                tarjeta=tarjeta, valor=body_dict["saldo_inicial"]
            )
        else:
            BalanceTarjetas.objects.create(tarjeta=tarjeta, valor=Decimal(0))

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

        # if body_dict["tipo"] == TipoTranferenciaChoices.EGRESO:
        #     try:
        #         tarjeta = validate_transferencia(id_tarjeta=body_dict["tarjeta"])
        #     except Http404:
        #         raise HttpError(404, "Tarjeta no encontrada")
        #     except Exception as e:
        #         raise HttpError(400, f"{e}")
        # else:
        tarjeta = get_object_or_404(Cuentas, pk=body_dict["tarjeta"])

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
                balance = BalanceTarjetas.objects.get(tarjeta=transferencia.cuenta)
                if (balance.valor - transferencia.cantidad) >= 0:
                    balance.valor = balance.valor - transferencia.cantidad
                    balance.save()
                else:
                    raise HttpError(400, "No hay saldo sufiente para esta acción")

                transferencia.delete()

        elif transferencia.tipo == TipoTranferenciaChoices.EGRESO:
            with transaction.atomic():
                balance = BalanceTarjetas.objects.get(tarjeta=transferencia.cuenta)
                balance.valor = balance.valor + transferencia.cantidad
                balance.save()

                transferencia.delete()

        return
