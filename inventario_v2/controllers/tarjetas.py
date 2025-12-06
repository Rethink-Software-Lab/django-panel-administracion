from ninja.errors import HttpError
from inventario.models import (
    User,
    Cuentas,
    Transacciones,
    TipoTranferenciaChoices,
)
from ..schema import (
    TransferenciasTarjetasModify,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from ..custom_permissions import isAdmin, isSupervisor
from django.db import transaction
from decimal import Decimal


@api_controller("tarjetas/", tags=["Tarjetas"], permissions=[isAdmin | isSupervisor])
class TarjetasController:
    """Esto son las transacciones [ingreso y egreso]"""

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
                if tarjeta.saldo < cantidad:
                    raise HttpError(400, "No hay saldo sufiente para esta accion")

                tarjeta.saldo -= cantidad
                tarjeta.save()

            Transacciones.objects.create(
                cuenta=tarjeta,
                cantidad=cantidad,
                descripcion=body_dict["descripcion"],
                tipo=body_dict["tipo"],
                usuario=usuario,
            )
