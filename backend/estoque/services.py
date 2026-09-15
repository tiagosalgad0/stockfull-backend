# Regras de negócio do controle de estoque

# Este módulo é o coração do domínio: concentra a regra de cálculo de compra
# (RN da falta, do vencimento e do caso normal) para que ela não fique
# espalhada entre controllers/views

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import FechamentoMensal, Ingrediente, RegistroEstoqueMensal

# Aplica 20% de margem quando houve falta para reduzir a chance de o problema se repetir
MARGEM_SEGURANCA_FALTA = Decimal("1.20")
# Centraliza o zero como Decimal para não misturar tipos nos cálculos financeiros
ZERO = Decimal("0")


def _dec(valor) -> Decimal:
    #Normaliza para Decimal — campos atribuídos em memória (fora de um save/refresh) podem
    #chegar como int, por isso as operações do domínio não confiam no tipo do atributo
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def arredondar(quantidade: Decimal, unidade: str) -> Decimal:
    # Unidades indivisíveis são arredondadas para cima; as demais mantêm casas decimais
    if unidade == Ingrediente.Unidade.UNIDADE:
        # Itens contáveis são comprados por inteiro, sempre arredondando para cima
        return quantidade.to_integral_value(rounding=ROUND_CEILING)
    # Para peso e volume, preserva duas casas usando o arredondamento comercial
    return quantidade.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_compra(ingrediente: Ingrediente, registro: RegistroEstoqueMensal) -> Decimal:
    # Regra central do sistema: prioridade FALTA > VENCIMENTO > NORMAL
    if registro.faltou:
        # A falta tem prioridade: usa o consumo real com margem, mesmo que a meta fosse menor
        quantidade = _dec(registro.consumo) * MARGEM_SEGURANCA_FALTA
    elif registro.venceu:
        # Se houve vencimento, repõe a meta inteira para substituir o estoque que se perdeu
        quantidade = _dec(ingrediente.meta)
    else:
        # No cenário normal, compra apenas o necessário para voltar à meta definida
        quantidade = _dec(ingrediente.meta) - _dec(registro.estoque_final)

    # Nunca retorna uma compra negativa quando o estoque final já passou da meta
    quantidade = max(quantidade, ZERO)
    return arredondar(quantidade, ingrediente.unidade)


def sugerir_nova_meta(registro: RegistroEstoqueMensal) -> Decimal | None:
    # Quando há falta, a meta anterior foi insuficiente; sugere consumo * 1.20
    if not registro.faltou:
        return None
    return arredondar(_dec(registro.consumo) * MARGEM_SEGURANCA_FALTA, registro.ingrediente.unidade)


def validar_registro(registro: RegistroEstoqueMensal) -> None:
    # Valida as regras também no domínio, protegendo-as além da camada HTTP
    if registro.consumo < ZERO:
        raise ValidationError("O consumo não pode ser negativo.")

    # Quando há falta, o consumo reportado pode representar a demanda que faltou
    # atender (por isso pode superar o estoque inicial). Fora desse caso, o consumo não pode exceder o que havia
    if not registro.faltou and registro.consumo > registro.estoque_inicial:
        raise ValidationError("O consumo não pode ser maior que o estoque inicial.")

    if registro.faltou and registro.data_falta is None:
        raise ValidationError("A data da falta é obrigatória quando faltou = true.")


def processar_registro(registro: RegistroEstoqueMensal) -> RegistroEstoqueMensal:
    # Calcula estoqueFinal, estoquePerdido e quantidadeCompra de um registro
    # Primeiro valida a entrada; os valores abaixo só são calculados para um registro coerente
    validar_registro(registro)
    ingrediente = registro.ingrediente

    if registro.faltou:
        # O estoque chegou a zero antes do fim do período: nada sobrou e nada foi perdido
        registro.estoque_final = ZERO
        registro.estoque_perdido = ZERO
    else:
        # Sem falta, o saldo é a diferença entre o inventário inicial e o consumo informado
        registro.estoque_final = _dec(registro.estoque_inicial) - _dec(registro.consumo)
        registro.estoque_perdido = registro.estoque_final if registro.venceu else ZERO

    # Finaliza o processamento aplicando a regra de compra conforme o cenário do registro
    registro.quantidade_compra = calcular_compra(ingrediente, registro)
    return registro


@transaction.atomic
def calcular_fechamento(fechamento: FechamentoMensal) -> list[RegistroEstoqueMensal]:
    # Processa todos os registros de um fechamento e persiste os valores calculados
    if not fechamento.esta_aberto:
        raise ValidationError("Um fechamento encerrado não pode ser recalculado.")

    # Carrega o ingrediente junto para não criar consultas repetidas dentro do laço
    registros = list(
        fechamento.registros.select_related("ingrediente").all()
    )
    for registro in registros:
        # Persiste somente os campos controlados por este cálculo
        processar_registro(registro)
        registro.save(update_fields=["estoque_final", "estoque_perdido", "quantidade_compra"])
    return registros


def encerrar_fechamento(fechamento: FechamentoMensal) -> FechamentoMensal:
    # Calcula todos os registros e encerra o fechamento
    if not fechamento.esta_aberto:
        raise ValidationError("Este fechamento já está encerrado.")

    if not fechamento.registros.exists():
        raise ValidationError("O fechamento não possui registros de estoque.")

    # Usa a data atual como referência para impedir uma falta registrada no futuro
    hoje = date.today()
    for registro in fechamento.registros.all():
        if registro.faltou and registro.data_falta and registro.data_falta > hoje:
            raise ValidationError(
                "A data da falta não pode ser posterior à data de encerramento."
            )

    # Recalcula antes de fechar para garantir que os dados gravados estejam atualizados
    calcular_fechamento(fechamento)

    fechamento.status = FechamentoMensal.Status.FECHADO
    fechamento.data_fechamento = timezone.now()
    fechamento.save(update_fields=["status", "data_fechamento"])
    return fechamento


@dataclass(frozen=True)
class ItemListaCompra:
    # Esta estrutura representa a visão enxuta enviada para a lista de compras
    ingrediente_id: int
    ingrediente: str
    quantidade: Decimal
    unidade: str


def gerar_lista_compras(fechamento: FechamentoMensal) -> list[ItemListaCompra]:
    # Consolida os ingredientes cuja quantidade de compra calculada é maior que zero
    itens = []
    registros = fechamento.registros.select_related("ingrediente").all()
    for registro in registros:
        # Reaplica o cálculo em memória para a lista refletir os dados mais recentes
        processar_registro(registro)
        if registro.quantidade_compra > ZERO:
            itens.append(
                ItemListaCompra(
                    ingrediente_id=registro.ingrediente_id,
                    ingrediente=registro.ingrediente.nome,
                    quantidade=registro.quantidade_compra,
                    unidade=registro.ingrediente.unidade,
                )
            )
    return itens


@dataclass(frozen=True)
class SugestaoMeta:
    # Esta estrutura deixa explícito o comparativo usado na decisão de ajustar a meta
    ingrediente_id: int
    ingrediente: str
    meta_atual: Decimal
    nova_meta_sugerida: Decimal


def gerar_sugestoes_metas(fechamento: FechamentoMensal) -> list[SugestaoMeta]:
    # Lista as sugestões de nova meta para ingredientes que tiveram falta no período (UC08)
    sugestoes = []
    # Somente ingredientes que faltaram podem gerar uma sugestão de aumento de meta
    registros = fechamento.registros.select_related("ingrediente").filter(faltou=True)
    for registro in registros:
        sugestoes.append(
            SugestaoMeta(
                ingrediente_id=registro.ingrediente_id,
                ingrediente=registro.ingrediente.nome,
                meta_atual=registro.ingrediente.meta,
                nova_meta_sugerida=sugerir_nova_meta(registro),
            )
        )
    return sugestoes


def atualizar_meta(ingrediente: Ingrediente, nova_meta: Decimal) -> Ingrediente:
    # Confirmação explícita de uma nova meta (UC08) — nunca um efeito colateral do cálculo
    if nova_meta <= ZERO:
        raise ValidationError("A nova meta deve ser maior que zero.")
    # Altera a meta somente quando a confirmação chega explicitamente por esta operação
    ingrediente.meta = nova_meta
    ingrediente.save(update_fields=["meta"])
    return ingrediente
