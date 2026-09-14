# Migração inicial do app `estoque`.
#
# As tabelas `ingrediente`, `fechamento` e `registro_estoque_mensal` já existem no
# banco de desenvolvimento/produção (criadas fora do Django, a partir do SQL de origem
# do projeto), com estrutura idêntica à gerada por este CreateModel (mesmos tipos,
# defaults, constraints e nomes de tabela — conferido por introspecção do banco real).
#
# Por isso, nesse ambiente esta migração é aplicada com `migrate --fake`: o Django
# passa a conhecer o estado dos models e registra a migração como aplicada, sem
# executar nenhum DDL — nada é criado, alterado ou apagado nas tabelas existentes.
#
# Em qualquer banco novo (ex.: banco de testes, CI, outra máquina), esta migração roda
# normalmente e cria as tabelas do zero com a mesma estrutura.

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ingrediente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, unique=True)),
                ('unidade', models.CharField(choices=[('KG', 'Quilograma'), ('L', 'Litro'), ('UN', 'Unidade')], max_length=30)),
                ('meta', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('prazo_validade_dias', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('ativo', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'ingrediente',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='FechamentoMensal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano', models.PositiveIntegerField()),
                ('mes', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)])),
                ('data_fechamento', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('ABERTO', 'Aberto'), ('FECHADO', 'Fechado')], default='ABERTO', max_length=10)),
            ],
            options={
                'db_table': 'fechamento',
                'ordering': ['-ano', '-mes'],
                'unique_together': {('ano', 'mes')},
            },
        ),
        migrations.CreateModel(
            name='RegistroEstoqueMensal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estoque_inicial', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('consumo', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('faltou', models.BooleanField(default=False)),
                ('data_falta', models.DateField(blank=True, null=True)),
                ('venceu', models.BooleanField(default=False)),
                ('estoque_final', models.DecimalField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('estoque_perdido', models.DecimalField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('quantidade_compra', models.DecimalField(blank=True, decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('fechamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registros', to='estoque.fechamentomensal')),
                ('ingrediente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='registros', to='estoque.ingrediente')),
            ],
            options={
                'db_table': 'registro_estoque_mensal',
                'ordering': ['ingrediente__nome'],
                'unique_together': {('fechamento', 'ingrediente')},
            },
        ),
    ]
