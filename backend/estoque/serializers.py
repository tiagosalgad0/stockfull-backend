from decimal import Decimal

from rest_framework import serializers

from .models import FechamentoMensal, Ingrediente, RegistroEstoqueMensal


class IngredienteSerializer(serializers.ModelSerializer):
    # Expõe todos os atributos que fazem parte do cadastro de ingredientes
    class Meta:
        model = Ingrediente
        fields = ["id", "nome", "unidade", "meta", "prazo_validade_dias", "ativo"]


class AtualizarMetaSerializer(serializers.Serializer):
    # Separa este payload para confirmar a meta sem abrir alteração dos demais campos
    nova_meta = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))


class FechamentoMensalSerializer(serializers.ModelSerializer):
    # Permite criar e consukltar períodos, mantendo o encerramento sob controle das regras
    class Meta:
        model = FechamentoMensal
        fields = ["id", "ano", "mes", "data_fechamento", "status"]
        read_only_fields = ["data_fechamento", "status"]

    def validate_mes(self, valor):
        # Reforça o intervalo de meses para devolver um erro claro pela API
        if not 1 <= valor <= 12:
            raise serializers.ValidationError("O mês deve estar entre 1 e 12.")
        return valor


class RegistroEstoqueMensalSerializer(serializers.ModelSerializer):
    # Acrescenta nome e unidade para a API não exigir uma consulta extra do ingrediente
    ingrediente_nome = serializers.CharField(source="ingrediente.nome", read_only=True)
    unidade = serializers.CharField(source="ingrediente.unidade", read_only=True)

    class Meta:
        # Os resultados do cálculo e o fechamento vêm sempre do fluxo do servidor
        model = RegistroEstoqueMensal
        fields = [
            "id",
            "fechamento",
            "ingrediente",
            "ingrediente_nome",
            "unidade",
            "estoque_inicial",
            "consumo",
            "faltou",
            "data_falta",
            "venceu",
            "estoque_final",
            "estoque_perdido",
            "quantidade_compra",
        ]
        read_only_fields = [
            "fechamento",
            "estoque_final",
            "estoque_perdido",
            "quantidade_compra",
        ]

    def validate(self, dados):
        # Combina valores novos e atuais para a validação funcionar em criação e edição parcial
        faltou = dados.get("faltou", getattr(self.instance, "faltou", False))
        consumo = dados.get("consumo", getattr(self.instance, "consumo", None))
        estoque_inicial = dados.get(
            "estoque_inicial", getattr(self.instance, "estoque_inicial", None)
        )
        data_falta = dados.get("data_falta", getattr(self.instance, "data_falta", None))

        if consumo is not None and consumo < 0:
            raise serializers.ValidationError({"consumo": "O consumo não pode ser negativo."})

        if not faltou and consumo is not None and estoque_inicial is not None and consumo > estoque_inicial:
            raise serializers.ValidationError(
                {"consumo": "O consumo não pode ser maior que o estoque inicial."}
            )

        if faltou and data_falta is None:
            raise serializers.ValidationError(
                {"data_falta": "A data da falta é obrigatória quando faltou = true."}
            )

        return dados


class ItemListaCompraSerializer(serializers.Serializer):
    # Serializa a projeção consolidada, que não precisa ser uma tabela própria
    ingrediente_id = serializers.IntegerField()
    ingrediente = serializers.CharField()
    quantidade = serializers.DecimalField(max_digits=10, decimal_places=2)
    unidade = serializers.CharField()


class SugestaoMetaSerializer(serializers.Serializer):
    # Entrega a comparação entre a meta atual e a sugestão calculada para a tomada de decisão
    ingrediente_id = serializers.IntegerField()
    ingrediente = serializers.CharField()
    meta_atual = serializers.DecimalField(max_digits=10, decimal_places=2)
    nova_meta_sugerida = serializers.DecimalField(max_digits=10, decimal_places=2)
