# Rotas globais que conectam o painel administrativo e a API de estoque
from django.contrib import admin
from django.urls import include, path

from .auth_views import LoginView, LogoutView, MeView

urlpatterns = [
    # Mantém o painel nativo disponível para administrar os dados manualmente
    path('admin/', admin.site.urls),
    # Login por token (usuário/senha do django.contrib.auth) para o frontend React
    path('api/auth/login/', LoginView.as_view(), name='api-login'),
    path('api/auth/logout/', LogoutView.as_view(), name='api-logout'),
    path('api/auth/me/', MeView.as_view(), name='api-me'),
    # Agrupa todos os endpoints do domínio sob um único prefixo da API
    path('api/', include('estoque.urls')),
]
