#!/usr/bin/env python
# Ponto de entrada para executar os comandos administrativos do Django
import os
import sys


def main():
    # Configura o projeto antes de repassar os argumentos ao Django
    # Define as configurações que todos os comandos (migrate, runserver e test) devem carregar
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockfull.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    # Executa o comando somente quando este arquivo é chamado diretamente
    main()
