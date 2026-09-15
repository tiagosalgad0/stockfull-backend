# Configurações da aplicação Stockfull

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Usa a raiz do projeto como referência para arquivos locais, como o banco SQLite
BASE_DIR = Path(__file__).resolve().parent.parent

# lê as variáveis do arquivo .env que fica só na máquina, assim nenhuma senha
# ou chave precisa ficar escrita direto aqui no código
load_dotenv(BASE_DIR / '.env')


# essa chave vem do ambiente porque ela é o que garante a segurança dos dados dos
# usuários, então não pode ficar visível pra quem olhar o código no servidor online
SECRET_KEY = os.environ.get(
    'SECRET_KEY', 'django-insecure-_-6f%a4^j_ts($8^a29g)9n-s*hs$kx-n4$bkhvxi^!b35ap0v'
)

# no site publicado precisa estar desligado, senão qualquer erro mostra detalhes internos do sistema pra
# quem estiver acessando
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# lista dos endereços que têm permissão de servir o site, um por vírgula na
# variável de ambiente
ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get('ALLOWED_HOSTS', '').split(',') if host.strip()
]


# Registra os componentes nativos, a API REST e a aplicação do domínio
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'usuarios',
    'estoque',
]

# Usuário customizado (tabela "usuario")
AUTH_USER_MODEL = 'usuarios.Usuario'

REST_FRAMEWORK = {
    # Limita as listas para que a API continue previsível mesmo com muitos registros
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    # Token simples via header Authorization: protege a API para o frontend React
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

MIDDLEWARE = [
    # Mantém a cadeia padrão do Django para segurança, sessão e proteção das requisições
    'django.middleware.security.SecurityMiddleware',
    # entrega os arquivos estáticos (css, admin) direto pelo próprio servidor Django, sem
    # precisar de outro serviço separado só pra isso
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # libera o frontend, quando estiver em outro endereço, a conversar com essa API
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# endereços do frontend que podem chamar essa API, um por vírgula na variável de ambiente
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]

# mesma ideia do CORS, mas para o Django confiar nesses endereços em formulários/requisições
# que alteram dados (proteção contra CSRF)
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

ROOT_URLCONF = 'stockfull.urls'

TEMPLATES = [
    # Permite que o Django encontre templates das aplicações caso a interface seja expandida
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'stockfull.wsgi.application'


# Estava usando o sqlite, mas troquei para PostgreSQL pra que não tenha problemas em hospedar online...
DATABASES = {
    'default': dj_database_url.config(
        default=(
            f"postgresql://{os.environ.get('DB_USER', 'postgres')}:"
            f"{os.environ.get('DB_PASSWORD', '')}@"
            f"{os.environ.get('DB_HOST', 'localhost')}:"
            f"{os.environ.get('DB_PORT', '5432')}/"
            f"{os.environ.get('DB_NAME', 'db_stockfull')}"
        ),
        conn_max_age=600,
    )
}


# Preserva os validadores padrão caso a autenticação seja usada
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Mantém as opções padrão de idioma e fuso enquanto não há exigência de localização específica
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Centraliza o prefixo dos arquivos estáticos para uma futura interface web
STATIC_URL = 'static/'
# pasta onde o comando "collectstatic" reúne todos os arquivos estáticos antes de publicar
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    # deixa os arquivos estáticos compactados e com nomes únicos, pra carregar mais rápido
    # e sem risco de o navegador mostrar uma versão antiga depois de uma atualização
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


# Proteções para quando o site já estiver publicado com endereço https

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # avisa o Django que quem garante a conexão segura é o serviço de hospedagem na
    # frente dele, e não ele mesmo
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# No desenvolvimento, envia e-mails ao console para não depender de um provedor externo
# (esse é o nome de configuração que o Django realmente reconhece)
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
