from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# O roteador do DRF expõe automaticamente as operações dos viewsets
router = DefaultRouter()
router.register("ingredientes", views.IngredienteViewSet, basename="ingrediente")
router.register("fechamentos", views.FechamentoMensalViewSet, basename="fechamento")

urlpatterns = [
    # Inclui as rotas CRUD geradas para ingredientes e fechamentos
    path("", include(router.urls)),
    # Estas duas rotas atendem aos registros dentro de cada fechamento
    path(
        "fechamentos/<int:fechamento_id>/estoques/",
        views.RegistroEstoqueListCreateView.as_view(),
        name="registro-estoque-list-create",
    ),
    path(
        "fechamentos/<int:fechamento_id>/estoques/<int:estoque_id>/",
        views.RegistroEstoqueDetailView.as_view(),
        name="registro-estoque-detail",
    ),
]
