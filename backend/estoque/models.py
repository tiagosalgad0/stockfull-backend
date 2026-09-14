from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Ingrediente(models.Model):
    # Item utilizado pelo restaurante, com uma meta de estoque a ser reposta a cada fechamento

    class Unidade(models.TextChoices):
        # Reúne as unidades permitidas para evitar valores livres e inconsistentes no banco.
        KG = "KG", "Quilograma"
        LITRO = "L", "Litro"
        UNIDADE = "UN", "Unidade"

    # Armazena os dados cadastrais e as regras mínimas de cada ingrediente.
    nome = models.CharField(max_length=150, unique=True)
    unidade = models.CharField(max_length=30, choices=Unidade.choices)
    meta = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    prazo_validade_dias = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    ativo = models.BooleanField(default=True)

    class Meta:
        # Tabela já existe no PostgreSQL (criada fora do Django) — não usar o nome padrão da app.
        db_table = "ingrediente"
        # Exibe ingredientes em ordem alfabética nas consultas e no admin.
        ordering = ["nome"]

    def __str__(self):
        # Retorna o nome para que as referências do Django sejam legíveis.
        return self.nome

    @property
    def aceita_decimal(self):
        # Informa quando o arredondamento precisa eliminar frações.
        # Unidades indivisíveis (ex.: unidade) não aceitam quantidades fracionárias
        return self.unidade != self.Unidade.UNIDADE


class FechamentoMensal(models.Model):
    # Encerramento de um mês de estoque, base para o cálculo das compras do período seguinte

    class Status(models.TextChoices):
        # Restringe o ciclo do fechamento aos dois estados que o fluxo suporta.
        ABERTO = "ABERTO", "Aberto"
        FECHADO = "FECHADO", "Fechado"

    # Identifica unicamente o período e registra quando ele foi efetivamente concluído.
    ano = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    # Coluna no banco é TIMESTAMP (não DATE) — DateField quebraria a serialização (ver auditoria).
    data_fechamento = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ABERTO
    )

    class Meta:
        # Tabela já existe no PostgreSQL (criada fora do Django) — não usar o nome padrão da app.
        db_table = "fechamento"
        # Ordena do mais recente e impede dois fechamentos para o mesmo mês.
        ordering = ["-ano", "-mes"]
        unique_together = ["ano", "mes"]

    def __str__(self):
        # Formata o período de modo compacto para o admin e mensagens.
        return f"{self.mes:02d}/{self.ano}"

    @property
    def esta_aberto(self):
        # Centraliza a consulta de estado para as regras não dependerem da string do status.
        return self.status == self.Status.ABERTO


class RegistroEstoqueMensal(models.Model):
    # Situação de um ingrediente dentro de um fechamento: o que entrou, o que saiu e o que comprar

    # Liga cada registro a um único período e protege ingredientes que já têm histórico.
    fechamento = models.ForeignKey(
        FechamentoMensal, on_delete=models.CASCADE, related_name="registros"
    )
    ingrediente = models.ForeignKey(
        Ingrediente, on_delete=models.PROTECT, related_name="registros"
    )

    # Armazena os valores informados no inventário do período.
    estoque_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    consumo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )

    faltou = models.BooleanField(default=False)
    data_falta = models.DateField(null=True, blank=True)
    venceu = models.BooleanField(default=False)

    # Campos calculados pelo domínio (estoque/services.py), preenchidos ao processar o registro.
    # A coluna no banco é NOT NULL DEFAULT 0 — antes de calcular o registro, 0 representa
    # "ainda não processado", equivalente ao NULL usado anteriormente.
    estoque_final = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"), blank=True
    )
    estoque_perdido = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"), blank=True
    )
    quantidade_compra = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"), blank=True
    )

    class Meta:
        # Tabela já existe no PostgreSQL (criada fora do Django) — não usar o nome padrão da app.
        db_table = "registro_estoque_mensal"
        # Mantém os itens ordenados e garante um único ingrediente por fechamento.
        ordering = ["ingrediente__nome"]
        unique_together = ["fechamento", "ingrediente"]

    def __str__(self):
        # Mostra a combinação mais útil ao consultar um registro no Django.
        return f"{self.ingrediente} - {self.fechamento}"
