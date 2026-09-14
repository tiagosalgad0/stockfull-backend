# Usuário customizado: mesma API do Django (TokenAuthentication, admin, permissões)
# mas gravando em colunas com nomes em português na tabela "usuario".
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, UserManager
from django.db import models
from django.utils import timezone


class Usuario(AbstractBaseUser, PermissionsMixin):
    username = models.CharField('usuario', max_length=150, unique=True, db_column='usuario')
    password = models.CharField('senha', max_length=128, db_column='senha')
    first_name = models.CharField('primeiro nome', max_length=150, blank=True, db_column='primeiro_nome')
    last_name = models.CharField('sobrenome', max_length=150, blank=True, db_column='sobrenome')
    email = models.EmailField('email', blank=True, db_column='email')
    is_staff = models.BooleanField('membro da equipe', default=False, db_column='membro_equipe')
    is_active = models.BooleanField('ativo', default=True, db_column='ativo')
    is_superuser = models.BooleanField('superusuario', default=False, db_column='superusuario')
    last_login = models.DateTimeField('ultimo login', blank=True, null=True, db_column='ultimo_login')
    date_joined = models.DateTimeField('data de cadastro', default=timezone.now, db_column='data_cadastro')

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'usuario'
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def __str__(self):
        return self.username
