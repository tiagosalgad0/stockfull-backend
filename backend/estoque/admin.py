from django.contrib import admin

from .models import FechamentoMensal, Ingrediente, RegistroEstoqueMensal


@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    # Organiza a tela de ingredientes para facilitar busca, filtro e conferência do cadastro.
    list_display = ["nome", "unidade", "meta", "prazo_validade_dias", "ativo"]
    list_filter = ["unidade", "ativo"]
    search_fields = ["nome"]


class RegistroEstoqueMensalInline(admin.TabularInline):
    # Exibe os registros dentro do fechamento, mantendo os valores calculados somente para leitura.
    model = RegistroEstoqueMensal
    extra = 0
    readonly_fields = ["estoque_final", "estoque_perdido", "quantidade_compra"]


@admin.register(FechamentoMensal)
class FechamentoMensalAdmin(admin.ModelAdmin):
    # Centraliza a consulta do período e de seus itens na mesma página do admin.
    list_display = ["__str__", "status", "data_fechamento"]
    list_filter = ["status"]
    inlines = [RegistroEstoqueMensalInline]


@admin.register(RegistroEstoqueMensal)
class RegistroEstoqueMensalAdmin(admin.ModelAdmin):
    # Disponibiliza uma visualização direta dos valores que influenciam a compra.
    list_display = [
        "ingrediente",
        "fechamento",
        "estoque_inicial",
        "consumo",
        "faltou",
        "venceu",
        "quantidade_compra",
    ]
    list_filter = ["faltou", "venceu", "fechamento"]
