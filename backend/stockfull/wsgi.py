# Entrada WSGI preparada para servidores web tradicionais

import os
import sys

# Garante que a pasta backend/ (pai deste arquivo) esteja no path, já que o
# Vercel importa este módulo sem rodar a partir de dentro de backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Garante que o servidor carregue as configurações corretas antes de iniciar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockfull.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
