# Stockfull

> Deixei um tutorial sobre como funciona o sistema e formatei no .md <3

Sistema de controle de estoque para restaurantes: cadastro de ingredientes, fechamento mensal de estoque e geração automática da lista de compras do próximo período.

O projeto é dividido em dois repositórios independentes, hospedados lado a lado nesta mesma pasta:

## API (Backend):
[`backend/`](backend/)
[stockfull-backend](https://github.com/tiagosalgad0/stockfull-backend)
[Vercel - Python serverless](https://stockfull-backend.vercel.app/)

## Interface (Frontend):
[`frontend/`](frontend/)
[stockfull-frontend](https://github.com/tiagosalgad0/stockfull-frontend)
[Vercel - site estático](https://stockfull-frontend.vercel.app/login)

## Banco de dados: 
**PostgreSQL** hospedado no **Supabase**.

Este README explica o projeto como um todo. Cada pasta tem, além disto, orientações específicas da sua parte (veja [`frontend/README.md`](frontend/README.md)).

---

## Sumário

- [O que o sistema faz](#o-que-o-sistema-faz)
- [Manual de uso (para quem nunca usou)](#manual-de-uso-para-quem-nunca-usou)
- [Como as compras são calculadas](#como-as-compras-são-calculadas)
- [Arquitetura](#arquitetura)
- [Stack técnica](#stack-técnica)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Instalação e execução local](#instalação-e-execução-local)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Hospedagem / deploy](#hospedagem--deploy)
- [Principais endpoints da API](#principais-endpoints-da-api)

---

## O que o sistema faz

O Stockfull ajuda quem administra o estoque de um restaurante a:

1. **Cadastrar os ingredientes** usados (nome, unidade de medida, meta de estoque e prazo de validade).
2. **Abrir um fechamento mensal** e registrar, para cada ingrediente, quanto tinha no início do mês, quanto foi consumido, se faltou e se venceu.
3. **Calcular automaticamente** quanto sobrou de cada ingrediente e quanto precisa ser comprado para repor a meta.
4. **Encerrar o período**, travando os dados daquele mês como histórico.
5. Consultar a **lista de compras** gerada e o **histórico** de fechamentos anteriores.

## Manual de uso

### 1. Entrar no sistema

Acesse o endereço do frontend e faça login com um usuário e senha cadastrados (veja como criar um usuário em [Instalação e execução local](#instalação-e-execução-local)). Não existe cadastro de conta pela própria tela — usuários são criados por um administrador.

### 2. Dashboard

É a tela inicial após o login. Mostra um resumo: quantos ingredientes estão cadastrados, quantos estão abaixo da meta, quantos estão em falta e quantos itens precisam ser comprados no período atual, além dos alertas mais urgentes.

### 3. Cadastrar ingredientes (menu "Estoque")

Antes de qualquer fechamento, cadastre os ingredientes que o restaurante usa. Para cada um, informe:

- **Nome** (precisa ser único);
- **Unidade**: Quilograma (KG), Litro (L) ou Unidade (UN);
- **Meta**: quantidade que deve existir em estoque depois de cada reposição;
- **Prazo de validade** (em dias).

Você pode editar ou excluir um ingrediente a qualquer momento — a exclusão só falha se ele já tiver histórico de fechamentos vinculado.

### 4. Abrir e preencher um fechamento (menu "Fechamentos")

No fim de cada mês:

1. Abra um novo período informando **ano** e **mês**.
2. Para cada ingrediente ativo, preencha a linha da tabela:
   - **Estoque inicial**: quanto havia no começo do período;
   - **Consumo**: quanto foi gasto no período;
   - **Falta**: marque se o ingrediente chegou a faltar antes do fim do mês (e informe a data da falta);
   - **Vencimento**: marque se o estoque restante venceu e teve de ser descartado.
3. Clique em **Calcular** quantas vezes quiser para ver o estoque final e a compra sugerida de cada item, conforme vai preenchendo.
4. Quando tudo estiver preenchido, clique em **Finalizar fechamento**. A partir daí o período fica travado (somente leitura) e passa a valer como histórico.

Se algum ingrediente teve falta, o sistema sugere uma nova meta para ele (para evitar que falte de novo) — essa sugestão aparece embaixo da tabela e só é aplicada se você clicar em **Confirmar nova meta**.

### 5. Lista de compras (menu "Compras")

Mostra, para o fechamento em andamento (ou o último realizado), tudo que precisa ser comprado: ingrediente, quantidade e se é um item crítico (que chegou a faltar).

### 6. Histórico (menu "Histórico")

Lista todos os fechamentos já realizados. Clique em "Ver detalhes" para consultar os registros completos de um período específico.

## Como as compras são calculadas

A regra de negócio (implementada em [`backend/estoque/services.py`](backend/estoque/services.py)) segue uma ordem de prioridade por ingrediente:

1. **Faltou** → compra o consumo registrado **+ 20% de margem de segurança**, mesmo que isso passe da meta (evita que a falta se repita).
2. **Venceu** (sem ter faltado) → compra a **meta inteira**, pois todo o estoque restante foi perdido.
3. **Caso normal** → compra apenas **meta − estoque final**, nunca um valor negativo.

Depois de calculada, a quantidade é arredondada: itens em **Unidade (UN)** sempre para cima (não se compra fração de um item); itens em **Kg** ou **Litro** mantêm duas casas decimais.

## Arquitetura

```
 Navegador
    │
    ▼
 Frontend (React + Vite)  ──►  estático, hospedado na Vercel
    │  fetch HTTP (JSON, token no header Authorization)
    ▼
 Backend (Django + DRF)   ──►  função serverless Python, hospedado na Vercel
    │  SQL (via pooler/pgbouncer)
    ▼
 PostgreSQL (Supabase)
```

- O frontend é uma **SPA** (Single Page Application) que consome a API REST do backend via `fetch`.
- A autenticação usa **token** do Django REST Framework: o token fica salvo no `localStorage` do navegador e é enviado em todo request no header `Authorization: Token <valor>`.
- Frontend e backend são publicados como **dois projetos separados na Vercel**, em domínios diferentes; por isso o backend precisa liberar explicitamente o domínio do frontend via CORS/CSRF (veja [Variáveis de ambiente](#variáveis-de-ambiente)).
- Em desenvolvimento local, o Vite faz *proxy* de `/api` para `http://127.0.0.1:8000`, então frontend e backend parecem estar na mesma origem e não há problema de CORS.

## Stack técnica

**Backend**
- Python + [Django](https://www.djangoproject.com/) (`>=6.1`) e [Django REST Framework](https://www.django-rest-framework.org/)
- Autenticação por token (`rest_framework.authtoken`)
- Modelo de usuário customizado (tabela em português) em `usuarios/`
- `psycopg` (driver PostgreSQL) + `dj-database-url` para configurar a conexão a partir de uma única `DATABASE_URL`
- `django-cors-headers` para liberar o frontend
- `whitenoise` para servir os arquivos estáticos do admin do Django sem depender de outro serviço
- `gunicorn` como servidor WSGI (usado em ambientes tipo Heroku; na Vercel quem executa é `@vercel/python`)

**Frontend**
- [React 19](https://react.dev/) + [Vite 8](https://vite.dev/) (build e dev server)
- [React Router 7](https://reactrouter.com/) para as rotas
- [Oxlint](https://oxc.rs/) para lint
- CSS puro, organizado por componente/feature (sem framework de UI)

**Infraestrutura**
- [Vercel](https://vercel.com/) hospeda os dois projetos (frontend como site estático, backend como função Python serverless)
- [Supabase](https://supabase.com/) hospeda o banco PostgreSQL

## Estrutura de pastas

```
stockfull/
├── backend/
│   ├── stockfull/        # settings, urls globais, autenticação (login/logout/me)
│   ├── usuarios/         # modelo de usuário customizado (tabela "usuario")
│   └── estoque/          # domínio principal
│       ├── models.py     # Ingrediente, FechamentoMensal, RegistroEstoqueMensal
│       ├── services.py   # regras de negócio (cálculo de compra, encerramento)
│       ├── views.py      # endpoints da API (DRF)
│       └── serializers.py
│
└── frontend/
    └── src/
        ├── app/           # rotas e providers globais (auth, toast)
        ├── components/    # componentes de UI e layout reutilizáveis
        ├── features/      # uma pasta por área do sistema
        │   ├── auth/
        │   ├── dashboard/
        │   ├── ingredientes/
        │   ├── fechamento/
        │   ├── compras/
        │   └── historico/
        ├── hooks/         # ex.: useEstoqueAtual (dados do período em andamento)
        └── services/api/  # cliente HTTP central (apiClient.js)
```

O backend segue uma separação clara entre **views** (camada HTTP) e **services** (regras de negócio), para que a lógica de cálculo não dependa do framework web. O frontend segue uma organização **por feature**: cada área do sistema tem suas próprias páginas, componentes e chamadas de API.

## Instalação e execução local

### Pré-requisitos

- [Python 3.12+](https://www.python.org/) e `pip`
- [Node.js 20+](https://nodejs.org/) e `npm`
- Um banco **PostgreSQL** acessível (pode ser local, ou um projeto gratuito no [Supabase](https://supabase.com/))

### 1. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# edite o .env: gere um SECRET_KEY, aponte para seu Postgres (DATABASE_URL ou DB_*),
# e para desenvolvimento defina DEBUG=True e ALLOWED_HOSTS=127.0.0.1,localhost

python manage.py migrate
python manage.py createsuperuser   # cria o primeiro usuário para conseguir logar
python manage.py runserver
```

A API sobe em `http://127.0.0.1:8000`. O admin do Django fica em `http://127.0.0.1:8000/admin/`.

### 2. Frontend

Em outro terminal:

```powershell
cd frontend
npm install

copy .env.example .env
# o valor padrão (VITE_API_URL=/api) já funciona em dev, pois o Vite
# encaminha /api para http://127.0.0.1:8000 automaticamente

npm run dev
```

Acesse `http://localhost:5173` e faça login com o usuário criado no passo anterior.

### Scripts úteis

| Comando | Onde | O que faz |
|---|---|---|
| `python manage.py runserver` | `backend/` | sobe a API em modo desenvolvimento |
| `python manage.py migrate` | `backend/` | aplica as migrações no banco |
| `python manage.py createsuperuser` | `backend/` | cria um usuário para login/admin |
| `python manage.py test` | `backend/` | roda os testes do backend |
| `npm run dev` | `frontend/` | sobe o frontend em modo desenvolvimento |
| `npm run build` | `frontend/` | gera o build de produção em `dist/` |
| `npm run preview` | `frontend/` | serve localmente o build gerado |
| `npm run lint` | `frontend/` | roda o Oxlint |

## Hospedagem / deploy

Ambos os projetos são publicados na **Vercel**, cada um a partir do seu próprio repositório GitHub.

**Backend** ([`backend/vercel.json`](backend/vercel.json)):
- Build via `@vercel/python`, servindo `stockfull/wsgi.py`.
- Antes do build, [`build_files.sh`](backend/build_files.sh) instala as dependências, roda `collectstatic` e aplica as migrações do banco automaticamente a cada deploy.
- As variáveis de ambiente (`SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `DEBUG=False`) são configuradas direto no painel do projeto na Vercel.
- Também há um [`Procfile`](backend/Procfile), mantido para compatibilidade com plataformas estilo Heroku, caso o backend precise migrar de hospedagem no futuro.

**Frontend** ([`frontend/vercel.json`](frontend/vercel.json)):
- Build padrão do Vite (`npm run build` → pasta `dist/`).
- `rewrites` redireciona todas as rotas para `index.html`, necessário porque é uma SPA com rotas do lado do cliente (React Router).
- A variável `VITE_API_URL` é configurada no painel da Vercel apontando para a URL pública do backend.

**Banco de dados**: PostgreSQL gerenciado pelo **Supabase**, acessado através do *connection pooler* (pgbouncer). Por causa de uma particularidade do pooler — ele às vezes entrega a conexão sem o `search_path` padrão — o backend fixa `search_path=public` explicitamente na configuração de conexão (veja o comentário em [`backend/stockfull/settings.py`](backend/stockfull/settings.py)).

## Principais endpoints da API

Todos sob o prefixo `/api/`, exigindo o header `Authorization: Token <token>` (exceto login).

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/auth/login/` | autentica e devolve o token |
| `POST` | `/auth/logout/` | invalida o token atual |
| `GET` | `/auth/me/` | dados do usuário autenticado |
| `GET/POST` | `/ingredientes/` | listar / cadastrar ingredientes |
| `GET/PUT/PATCH/DELETE` | `/ingredientes/{id}/` | consultar / editar / excluir um ingrediente |
| `PUT` | `/ingredientes/{id}/meta/` | confirmar uma nova meta sugerida |
| `GET/POST` | `/fechamentos/` | listar / abrir um fechamento |
| `GET` | `/fechamentos/{id}/` | detalhes de um fechamento |
| `GET/POST` | `/fechamentos/{id}/estoques/` | listar / registrar o estoque de um ingrediente no período |
| `PUT` | `/fechamentos/{id}/estoques/{id}/` | corrigir um registro (só com o fechamento aberto) |
| `POST` | `/fechamentos/{id}/calcular/` | recalcula estoque final e compras de todos os registros |
| `POST` | `/fechamentos/{id}/encerrar/` | calcula e encerra o período (fica somente leitura) |
| `GET` | `/fechamentos/{id}/lista-compras/` | lista de compras consolidada do período |
| `GET` | `/fechamentos/{id}/sugestoes-metas/` | sugestões de nova meta para itens que faltaram |
