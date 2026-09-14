# Entrada WSGI preparada para servidores web tradicionais

import os

from django.core.wsgi import get_wsgi_application

# Garante que o servidor carregue as configurações corretas antes de iniciar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockfull.settings')

application = get_wsgi_application()
