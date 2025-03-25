from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


def transfer_and_clean_data(apps, schema_editor):
    # Obtener modelos antiguos y nuevos
    Tarjetas = apps.get_model("inventario", "Tarjetas")
    Cuentas = apps.get_model("inventario", "Cuentas")
    BalanceTarjetas = apps.get_model("inventario", "BalanceTarjetas")
    TransferenciasTarjetas = apps.get_model("inventario", "TransferenciasTarjetas")

    # 1. Crear un mapeo de tarjetas a cuentas por ID
    tarjeta_a_cuenta = {}
    for tarjeta in Tarjetas.objects.all():
        cuenta = Cuentas.objects.create(
            nombre=tarjeta.nombre, banco=tarjeta.banco, tipo="BANCARIA", saldo=0.00
        )
        tarjeta_a_cuenta[tarjeta.id] = cuenta

    # 2. Actualizar BalanceTarjetas usando el mapeo
    for balance in BalanceTarjetas.objects.all():
        if balance.tarjeta_id in tarjeta_a_cuenta:
            balance.nueva_cuenta = tarjeta_a_cuenta[balance.tarjeta_id]
            balance.save()
        else:
            # Eliminar balances sin tarjeta correspondiente
            balance.delete()

    # 3. Actualizar TransferenciasTarjetas usando el mapeo
    for transferencia in TransferenciasTarjetas.objects.all():
        if transferencia.tarjeta_id in tarjeta_a_cuenta:
            transferencia.nueva_cuenta = tarjeta_a_cuenta[transferencia.tarjeta_id]
            transferencia.save()
        else:
            # Eliminar transferencias sin tarjeta correspondiente
            transferencia.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0046_vendedorexterno"),
    ]

    operations = [
        migrations.CreateModel(
            name="Cuentas",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nombre", models.CharField(max_length=50)),
                (
                    "tipo",
                    models.CharField(
                        choices=[("EFECTIVO", "Efectivo"), ("BANCARIA", "Bancaria")],
                        max_length=30,
                    ),
                ),
                (
                    "saldo",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=12
                    ),
                ),
                (
                    "banco",
                    models.CharField(
                        choices=[("BPA", "BPA"), ("BANDEC", "Bandec")], max_length=50
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="balancetarjetas",
            name="nueva_cuenta",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="balance",
                to="inventario.cuentas",
            ),
        ),
        migrations.AddField(
            model_name="transferenciastarjetas",
            name="nueva_cuenta",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="inventario.cuentas",
            ),
        ),
        migrations.RunPython(transfer_and_clean_data),
        migrations.RemoveField(
            model_name="balancetarjetas",
            name="tarjeta",
        ),
        migrations.RemoveField(
            model_name="transferenciastarjetas",
            name="tarjeta",
        ),
        migrations.RenameField(
            model_name="balancetarjetas",
            old_name="nueva_cuenta",
            new_name="cuenta",
        ),
        migrations.RenameField(
            model_name="transferenciastarjetas",
            old_name="nueva_cuenta",
            new_name="cuenta",
        ),
        migrations.DeleteModel(
            name="Tarjetas",
        ),
    ]
