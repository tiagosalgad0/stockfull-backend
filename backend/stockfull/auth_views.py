# Views mínimas de autenticação para o frontend React (fora do domínio de estoque)
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class LoginView(ObtainAuthToken):
    # Precisa ficar aberta: a permissão global do projeto é IsAuthenticated,
    # o que bloquearia o próprio login se não sobrescrevermos aqui
    permission_classes = [AllowAny]


class MeView(APIView):
    # Confirma o token e devolve os dados do usuário autenticado

    def get(self, request):
        return Response({"id": request.user.id, "username": request.user.username})


class LogoutView(APIView):
    # Invalida o token atual para que a sessão não continue utilizável após sair

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=204)
