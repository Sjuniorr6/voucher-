# Generated by Django 5.1.2 on 2024-10-14 12:16

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Motorista',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('cpf', models.CharField(max_length=11, unique=True)),
                ('placa_veiculo', models.CharField(max_length=7)),
                ('rota', models.CharField(max_length=100)),
            ],
        ),
    ]
