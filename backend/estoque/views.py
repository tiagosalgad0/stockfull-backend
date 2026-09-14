from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import FechamentoMensal, Ingrediente, RegistroEstoqueMensal
from .serializers import (
    AtualizarMetaSerializer,
    FechamentoMensalSerializer,
    IngredienteSerializer,
    ItemListaCompraSerializer,
    RegistroEstoqueMensalSerializer,
    SugestaoMetaSerializer,
)


class IngredienteViewSet(viewsets.ModelViewSet):
    # UC01, UC02, UC03 — cadastrar, consultar e alterar ingredientes

    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer

    @action(detail=True, methods=["put"], url_path="meta")
    def meta(self, request, pk=None):
        # UC08 — confirmação explícita de uma nova meta sugerida
        # Valida um payload exclusivo para evitar que esta ação altere outros dados do ingrediente
        ingrediente = self.get_object()
        serializer = AtualizarMetaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.atualizar_meta(ingrediente, serializer.validated_data["nova_meta"])
        except DjangoValidationError as erro:
            return Response({"detail": erro.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(IngredienteSerializer(ingrediente).data)


class FechamentoMensalViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    # UC04 — iniciar fechamento mensal, e consultas de fechamentos
    # Fechamentos não são alterados/excluídos diretamente (CA08): o encerramento
    # e o cálculo têm ações próprias, explícitas no domínio

    # Expõe apenas criação e consulta; cálculo e encerramento ficam em ações nomeadas
    queryset = FechamentoMensal.objects.all()
    serializer_class = FechamentoMensalSerializer

    @action(detail=True, methods=["post"], url_path="calcular")
    def calcular(self, request, pk=None):
        # UC06 — calcula a quantidade de compra de todos os registros do fechamento
        # Delega as regras ao serviço e converte erros de domínio em resposta HTTP apropriada
        fechamento = self.get_object()
        try:
            registros = services.calcular_fechamento(fechamento)
        except DjangoValidationError as erro:
            return Response({"detail": erro.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RegistroEstoqueMensalSerializer(registros, many=True).data)

    @action(detail=True, methods=["post"], url_path="encerrar")
    def encerrar(self, request, pk=None):
        # UC09 — encerra o fechamento após todos os registros estarem preenchidos
        # O serviço garante todas as pré-condições antes de mudar o estado do fechamento
        fechamento = self.get_object()
        try:
            services.encerrar_fechamento(fechamento)
        except DjangoValidationError as erro:
            return Response({"detail": erro.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FechamentoMensalSerializer(fechamento).data)

    @action(detail=True, methods=["get"], url_path="lista-compras")
    def lista_compras(self, request, pk=None):
        # UC07 — gera a lista de compras consolidada do fechamento
        # Retorna a projeção de compras, em vez de expor diretamente os registros internos
        fechamento = self.get_object()
        itens = services.gerar_lista_compras(fechamento)
        return Response(ItemListaCompraSerializer(itens, many=True).data)

    @action(detail=True, methods=["get"], url_path="sugestoes-metas")
    def sugestoes_metas(self, request, pk=None):
        # UC08 — sugestões de nova meta para ingredientes que tiveram falta
        # Mantém a sugestão separada da confirmação para que o ajuste continue intencional
        fechamento = self.get_object()
        sugestoes = services.gerar_sugestoes_metas(fechamento)
        return Response(SugestaoMetaSerializer(sugestoes, many=True).data)


class RegistroEstoqueListCreateView(APIView):
    # UC05 — registrar a situação mensal de um ingrediente dentro do fechamento

    def get(self, request, fechamento_id):
        # Busca o fechamento com segurança e carrega o ingrediente para a resposta completa
        fechamento = get_object_or_404(FechamentoMensal, pk=fechamento_id)
        registros = fechamento.registros.select_related("ingrediente").all()
        return Response(RegistroEstoqueMensalSerializer(registros, many=True).data)

    def post(self, request, fechamento_id):
        fechamento = get_object_or_404(FechamentoMensal, pk=fechamento_id)
        # Não aceita novos dados após o encerramento, preservando o histórico mensal
        if not fechamento.esta_aberto:
            return Response(
                {"detail": "Não é possível registrar estoque em um fechamento encerrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RegistroEstoqueMensalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registro = serializer.save(fechamento=fechamento)
        return Response(
            RegistroEstoqueMensalSerializer(registro).data, status=status.HTTP_201_CREATED
        )


class RegistroEstoqueDetailView(APIView):
    # PUT /api/fechamentos/{id}/estoques/{estoqueId} — corrige um registro do fechamento aberto

    def get_registro(self, fechamento_id, estoque_id):
        # Confere a associação ao fechamento para impedir acessar um registro de outro período
        return get_object_or_404(
            RegistroEstoqueMensal, pk=estoque_id, fechamento_id=fechamento_id
        )

    def put(self, request, fechamento_id, estoque_id):
        registro = self.get_registro(fechamento_id, estoque_id)
        if not registro.fechamento.esta_aberto:
            return Response(
                {"detail": "Não é possível alterar um registro de um fechamento encerrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Aceita correções parciais enquanto o período ainda está aberto
        serializer = RegistroEstoqueMensalSerializer(registro, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
