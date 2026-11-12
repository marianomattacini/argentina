from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('juego', '0009_jugador_reagrupamientos_turno'),
    ]

    operations = [
        migrations.AddField(
            model_name='partida',
            name='iniciada',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='partida',
            name='turno_inicio',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
