from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APITestCase

from . import services
from .models import FechamentoMensal, Ingrediente, RegistroEstoqueMensal


class CalcularCompraTests(TestCase):

    def setUp(self):
        # Reutiliza o mesmo período para manter cada cenário focado na regra testada
        self.fechamento = FechamentoMensal.objects.create(ano=2026, mes=8)

    def _registro(self, ingrediente, **kwargs):
        # Centraliza a criação de registros para os testes declararem somente o que muda em cada caso
        dados = {"fechamento": self.fechamento, "ingrediente": ingrediente}
        dados.update(kwargs)
        return RegistroEstoqueMensal.objects.create(**dados)

    def test_ca01_operacao_normal(self):
        # Confirma a reposição até a meta quando não houve falta nem vencimento
        ingrediente = Ingrediente.objects.create(
            nome="Farinha", unidade=Ingrediente.Unidade.KG, meta=50, prazo_validade_dias=30
        )
        registro = self._registro(ingrediente, estoque_inicial=50, consumo=30)
        services.processar_registro(registro)
        self.assertEqual(registro.estoque_final, Decimal("20"))
        self.assertEqual(registro.quantidade_compra, Decimal("30.00"))

    def test_ca02_vencimento(self):
        # Confirma que o saldo vencido é perdido e a compra recompõe a meta inteira
        ingrediente = Ingrediente.objects.create(
            nome="Leite", unidade=Ingrediente.Unidade.LITRO, meta=50, prazo_validade_dias=10
        )
        registro = self._registro(ingrediente, estoque_inicial=40, consumo=20, venceu=True)
        services.processar_registro(registro)
        self.assertEqual(registro.estoque_final, Decimal("20"))
        self.assertEqual(registro.estoque_perdido, Decimal("20"))
        self.assertEqual(registro.quantidade_compra, Decimal("50.00"))

    def test_ca03_falta(self):
        # Confirma que a falta zera o saldo e aplica a margem de segurança ao consumo
        ingrediente = Ingrediente.objects.create(
            nome="Arroz", unidade=Ingrediente.Unidade.KG, meta=40, prazo_validade_dias=60
        )
        registro = self._registro(
            ingrediente,
            estoque_inicial=50,
            consumo=60,
            faltou=True,
            data_falta=date(2026, 8, 20),
        )
        services.processar_registro(registro)
        self.assertEqual(registro.estoque_final, Decimal("0"))
        self.assertEqual(registro.quantidade_compra, Decimal("72.00"))

    def test_ca04_quantidade_zero_nao_aparece_na_lista(self):
        # Evita poluir a lista de compras com itens que não precisam de reposição
        ingrediente = Ingrediente.objects.create(
            nome="Sal", unidade=Ingrediente.Unidade.KG, meta=10, prazo_validade_dias=365
        )
        self._registro(ingrediente, estoque_inicial=10, consumo=0)
        itens = services.gerar_lista_compras(self.fechamento)
        self.assertEqual(itens, [])

    def test_ca05_arredondamento_unidade_indivisivel(self):
        # Verifica que itens inteiros nunca geram uma quantidade fracionada de compra
        ingrediente = Ingrediente.objects.create(
            nome="Ovos", unidade=Ingrediente.Unidade.UNIDADE, meta=300, prazo_validade_dias=20
        )
        registro = self._registro(
            ingrediente,
            estoque_inicial=300,
            consumo=340,
            faltou=True,
            data_falta=date(2026, 8, 15),
        )
        services.processar_registro(registro)
        self.assertEqual(registro.quantidade_compra, Decimal("408"))

    def test_ca06_lista_compras_tem_quantidade_e_unidade(self):
        # Verifica os campos que tornam a lista utilizável para quem vai comprar
        ingrediente = Ingrediente.objects.create(
            nome="Farinha", unidade=Ingrediente.Unidade.KG, meta=50, prazo_validade_dias=30
        )
        self._registro(ingrediente, estoque_inicial=50, consumo=32)
        itens = services.gerar_lista_compras(self.fechamento)
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0].quantidade, Decimal("32.00"))
        self.assertEqual(itens[0].unidade, "KG")

    def test_ca07_sugestao_nova_meta_na_falta(self):
        # Verifica que uma falta transforma o consumo observado em sugestão com margem
        ingrediente = Ingrediente.objects.create(
            nome="Arroz", unidade=Ingrediente.Unidade.KG, meta=40, prazo_validade_dias=60
        )
        registro = self._registro(
            ingrediente,
            estoque_inicial=50,
            consumo=60,
            faltou=True,
            data_falta=date(2026, 8, 20),
        )
        services.processar_registro(registro)
        self.assertEqual(services.sugerir_nova_meta(registro), Decimal("72.00"))

    def test_ca08_fechamento_encerrado_nao_pode_ser_recalculado(self):
        # Protege a imutabilidade do resultado depois que o período foi encerrado
        ingrediente = Ingrediente.objects.create(
            nome="Farinha", unidade=Ingrediente.Unidade.KG, meta=50, prazo_validade_dias=30
        )
        self._registro(ingrediente, estoque_inicial=50, consumo=32)
        services.encerrar_fechamento(self.fechamento)
        self.fechamento.refresh_from_db()
        self.assertEqual(self.fechamento.status, FechamentoMensal.Status.FECHADO)
        with self.assertRaises(ValidationError):
            services.calcular_fechamento(self.fechamento)


class ValidarRegistroTests(TestCase):
    # Isola as entradas inválidas para documentar os limites aceitos pelo domínio
    def setUp(self):
        # Monta os objetos básicos que os três cenários de validação compartilham
        self.fechamento = FechamentoMensal.objects.create(ano=2026, mes=9)
        self.ingrediente = Ingrediente.objects.create(
            nome="Farinha", unidade=Ingrediente.Unidade.KG, meta=50, prazo_validade_dias=30
        )

    def test_consumo_negativo_invalido(self):
        # Confirma que consumo negativo não representa uma movimentação válida de estoque
        registro = RegistroEstoqueMensal(
            fechamento=self.fechamento,
            ingrediente=self.ingrediente,
            estoque_inicial=10,
            consumo=-1,
        )
        with self.assertRaises(ValidationError):
            services.validar_registro(registro)

    def test_consumo_maior_que_estoque_sem_falta_invalido(self):
        # Confirma que, sem falta registrada, o consumo não supera o saldo inicial
        registro = RegistroEstoqueMensal(
            fechamento=self.fechamento,
            ingrediente=self.ingrediente,
            estoque_inicial=10,
            consumo=20,
            faltou=False,
        )
        with self.assertRaises(ValidationError):
            services.validar_registro(registro)

    def test_consumo_maior_que_estoque_com_falta_e_valido(self):
        # Confirma que, com falta, o consumo pode representar a demanda não atendida
        registro = RegistroEstoqueMensal(
            fechamento=self.fechamento,
            ingrediente=self.ingrediente,
            estoque_inicial=10,
            consumo=20,
            faltou=True,
            data_falta=date(2026, 9, 10),
        )
        services.validar_registro(registro)  # não deve levantar exceção


class ApiFluxoCompletoTests(APITestCase):
    # Exercita o fluxo via API: cadastro, fechamento, registro, cálculo e lista de compras

    def setUp(self):
        # A API exige autenticação, os testes de fluxo simulam um usuário já logado
        usuario = get_user_model().objects.create_user(username="teste", password="senha123")
        self.client.force_authenticate(user=usuario)

    def test_fluxo_completo(self):
        # Exercita o caminho completo, do cadastro ao bloqueio após o encerramento
        # Cria o ingrediente que será acompanhado neste fechamento
        resposta = self.client.post(
            "/api/ingredientes/",
            {"nome": "Farinha de trigo", "unidade": "KG", "meta": "50", "prazo_validade_dias": 30},
        )
        self.assertEqual(resposta.status_code, 201)
        ingrediente_id = resposta.data["id"]

        # Abre o período antes de registrar a situação do estoque
        resposta = self.client.post("/api/fechamentos/", {"ano": 2026, "mes": 8})
        self.assertEqual(resposta.status_code, 201)
        fechamento_id = resposta.data["id"]

        resposta = self.client.post(
            f"/api/fechamentos/{fechamento_id}/estoques/",
            {"ingrediente": ingrediente_id, "estoque_inicial": "50", "consumo": "32"},
        )
        self.assertEqual(resposta.status_code, 201)

        # Calcula e confere a compra mostrada na lista consolidada
        resposta = self.client.post(f"/api/fechamentos/{fechamento_id}/calcular/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data[0]["quantidade_compra"], "32.00")

        resposta = self.client.get(f"/api/fechamentos/{fechamento_id}/lista-compras/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data[0]["ingrediente"], "Farinha de trigo")
        self.assertEqual(resposta.data[0]["quantidade"], "32.00")

        # Ao encerrar, verifica que a API bloqueia novas inclusões naquele período
        resposta = self.client.post(f"/api/fechamentos/{fechamento_id}/encerrar/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["status"], "FECHADO")

        resposta = self.client.post(
            f"/api/fechamentos/{fechamento_id}/estoques/",
            {"ingrediente": ingrediente_id, "estoque_inicial": "10", "consumo": "5"},
        )
        self.assertEqual(resposta.status_code, 400)

    def test_confirmar_nova_meta(self):
        # Confirma que a sugestão só vira meta depois de uma chamada explícita do usuário
        resposta = self.client.post(
            "/api/ingredientes/",
            {"nome": "Arroz", "unidade": "KG", "meta": "40", "prazo_validade_dias": 60},
        )
        ingrediente_id = resposta.data["id"]

        resposta = self.client.put(
            f"/api/ingredientes/{ingrediente_id}/meta/", {"nova_meta": "72.00"}
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["meta"], "72.00")
