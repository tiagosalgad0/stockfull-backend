# Entrada ASGI preparada para servidores assíncronos

import os

from django.core.asgi import get_asgi_application

# Aponta o Django para as configurações do projeto antes de criar a aplicação ASGI
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockfull.settings')

application = get_asgi_application()
