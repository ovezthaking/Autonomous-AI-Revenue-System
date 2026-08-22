# Dzień 1 — Fundament (walking skeleton infrastruktury)

Cel dnia: `docker compose up` i **żyjąca infrastruktura bez logiki biznesowej**.
Żaden agent, żadne LangChain, żaden scraping, żaden HITL.

Po tym dniu każda kolejna funkcja ma gdzie mieszkać.

**Toolchain Pythona:** [uv](https://docs.astral.sh/uv/) (lockfile + venv + Docker) i [Ruff](https://docs.astral.sh/ruff/) (lint + format). **Nie używamy pip /** `requirements.txt` **/ venv ręcznie.**

**Definicja sukcesu**

- `docker compose ps` pokazuje `postgres`, `redis`, `ollama`, `backend` jako running / healthy
- `curl http://localhost:8000/health` zwraca `{"status":"ok"}`
- Postgres przyjmuje połączenie
- Redis odpowiada `PONG`
- Ollama nasłuchuje na porcie `11434` **bez** pobranego modelu
- lokalnie: `uv lock` ma `backend/uv.lock`, `uv run ruff check app` wychodzi czysto

Czas: 2–5 godzin. Nie ciągnij Ollamy (`ollama pull`) — to nie jest zadanie Dnia 1.

---



## 0. Czego nie robić dziś

- nie pisz agentów ani folderów z logiką research/content
- nie instaluj LangChain
- nie twórz tabel SQLAlchemy „na serio” (affiliate, HITL)
- nie stawiaj Celery workera (Redis wystarczy, że stoi)
- nie pobieraj modelu Ollama
- nie buduj dashboardu Next.js (wystarczy pusty katalog `frontend/`)
- nie konfiguruj Slack/Discord
- nie dodawaj `requirements.txt` ani `pip install` (ani w Dockerfile)

---



## 1. Wymagania na maszynie

Sprawdź, zanim cokolwiek skopiujesz:

```bash
docker --version
docker compose version
git --version
curl --version
uv --version
```

Potrzebujesz:

- Docker Engine + Docker Compose v2
- **uv** na hoście (generuje `uv.lock`; obraz Dockera ma własne uv)
- wolne porty: `5432` (Postgres), `6379` (Redis), `8000` (FastAPI), `11434` (Ollama)
- ~2 GB RAM na same kontenery bez modelu LLM

Jeśli `uv --version` nie działa:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Potem otwórz nowy terminal albo `source` ścieżki, którą podał installer (zwykle `~/.local/bin`).

Jeśli port jest zajęty, w `docker-compose.yml` zmień mapowanie po lewej stronie, np. `"5433:5432"`.

Praca odbywa się w **istniejącym** repo:

```bash
cd /home/ovezo/REPOS/Autonomous-AI-Revenue-System
```

Nie rób `git init` ani katalogu `revenue-swarm/`.

---



## 2. Szkielet katalogów

```bash
cd /home/ovezo/REPOS/Autonomous-AI-Revenue-System

mkdir -p backend/app/{api,models,services}
mkdir -p agents shared frontend

touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch agents/.gitkeep shared/.gitkeep frontend/.gitkeep
```

Docelowa struktura po Dniu 1:

```
Autonomous-AI-Revenue-System/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── backend/
│   ├── .dockerignore
│   ├── .python-version
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock              # commitujemy — to źródło prawdy wersji
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       ├── models/
│       └── services/
├── frontend/          # pusty, Faza 2
├── agents/            # pusty, Faza 3
├── shared/            # pusty, Faza 1+
└── docs/
    ├── requirements_architecture.md
    └── day1_fundament.md
```

Katalogi `api/`, `models/`, `services/` zostają puste (same `__init__.py`). Logika Dnia 1 jest tylko w `main.py`.

`.venv` w `backend/` powstanie po `uv sync` — git go ignoruje (wpis w `.gitignore`).

---



## 3. Pliki — twórz w tej kolejności



### 3.1. `backend/.python-version`

```text
3.12
```

uv i lokalne `uv sync` wezmą tę wersję.

### 3.2. `backend/pyproject.toml`

Projekt **nie** jest instalowalnym pakietem (`package = false`) — to aplikacja z `app/main.py`. Zależności runtime vs narzędzia (Ruff) są rozdzielone: obraz Dockera instaluje się z `--no-dev`.

```toml
[project]
name = "revenue-swarm-backend"
version = "0.1.0"
description = "Revenue Swarm API"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0,<1.0.0",
    "uvicorn[standard]>=0.32.0,<1.0.0",
]

[dependency-groups]
dev = [
    "ruff>=0.12.0",
]

[tool.uv]
package = false

[tool.ruff]
target-version = "py312"
line-length = 88
src = ["app"]

[tool.ruff.lint]
select = [
    "E",  # pycodestyle
    "F",  # pyflakes
    "I",  # isort
    "UP", # pyupgrade
    "B",  # bugbear
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```



### 3.3. `backend/app/main.py`

```python
from fastapi import FastAPI

app = FastAPI(title="Revenue Swarm API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```



### 3.4. Lockfile i venv na hoście

Z katalogu `backend/` (uv musi zobaczyć `pyproject.toml`):

```bash
cd backend
uv lock
uv sync
uv run ruff check app
uv run ruff format app
```

- `uv lock` → tworzy `uv.lock` (commitniesz go razem z `pyproject.toml`)
- `uv sync` → `.venv` + zależności **łącznie z grupą** `dev` (Ruff)
- Docker później robi `uv sync --locked --no-dev` — bez Ruffa w obrazie API

Jeśli `ruff check` zgłosi importy, odpal `uv run ruff check --fix app`. Ma wyjść bez błędów, zanim zbudujesz obraz.

Szybki sanity check API **bez** Dockera (opcjonalnie, Postgres nie jest potrzebny do `/health`):

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

W drugim terminalu: `curl -s http://127.0.0.1:8000/health`. Potem zatrzymaj uvicorn (`Ctrl+C`), żeby port 8000 był wolny dla Compose.

Wróć do korzenia repo:

```bash
cd ..
```



### 3.5. `backend/Dockerfile`

Obraz dostaje binarne uv z oficjalnego obrazu, lockfile jest źródłem prawdy, grupa `dev` nie wchodzi do runtime.

```dockerfile
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Uwagi:

- `--locked` = build pada, jeśli `uv.lock` nie zgadza się z `pyproject.toml` (najpierw `uv lock` na hoście).
- `--no-dev` = Ruff zostaje na maszynie deweloperskiej, nie w kontenerze API.
- `--no-install-project` = nie instalujemy „paczki” backendu; kod jest kopiowany jako `app/`.
- `PATH` wskazuje na `.venv` z `uv sync`, więc healthcheck Compose może wołać `python`.
- Tag `uv:0.8` przypnij świadomie; `:latest` w Dockerfile później rozjeżdża buildy.

W obrazie slim nie ma `curl`. Healthcheck w Compose użyje Pythona (krok 3.8).

### 3.6. `backend/.dockerignore`

```text
__pycache__
*.pyc
.venv
.env
.ruff_cache
```

Nie ignoruj `uv.lock`.

### 3.7. `.env.example`

Skopiuj do `.env` lokalnie. Pliku `.env` **nie commituj** (jest w `.gitignore`).

```bash
POSTGRES_USER=swarm
POSTGRES_PASSWORD=swarm
POSTGRES_DB=swarm
POSTGRES_PORT=5432

REDIS_PORT=6379

BACKEND_PORT=8000

OLLAMA_PORT=11434
```

Potem:

```bash
cp .env.example .env
```

Na razie hasło może być słabe — to środowisko lokalne. Przed wystawieniem na VPS zmień `POSTGRES_PASSWORD`.

### 3.8. `docker-compose.yml`

Wklej całość (plik w repo jest pusty):

```yaml
name: revenue-swarm

services:
  postgres:
    image: postgres:16-alpine
    env_file: .env
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "${REDIS_PORT}:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "${OLLAMA_PORT}:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    ports:
      - "${BACKEND_PORT}:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')",
        ]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

volumes:
  postgres_data:
  ollama_data:
```

Uwagi:

- `depends_on` backendu czeka na **healthy** Postgres i Redis. Ollama nie blokuje startu API — model i tak nie jest potrzebny.
- Dane Postgres i Ollama są w named volumes, nie w katalogu repo.
- Nie ma `command: ollama pull ...`. Pull to osobna decyzja po Dniu 1.

---



## 4. Uruchomienie

Z katalogu głównego repo (po `uv lock` w `backend/`):

```bash
cp .env.example .env   # jeśli jeszcze nie skopiowałeś

docker compose build
docker compose up -d
```

Pierwszy `up` ściąga obrazy (Postgres, Redis, Ollama, Python, warstwa uv). To może zająć kilka minut. Ollama jest dużym obrazem — poczekaj, nie przerywaj.

Logi:

```bash
docker compose ps
docker compose logs -f
```

`Ctrl+C` w `logs -f` tylko odłącza podgląd, kontenery działają dalej.

Codzienna pętla przy zmianie zależności:

```bash
cd backend
# edytuj pyproject.toml
uv lock
uv sync
cd ..
docker compose build backend
docker compose up -d backend
```

---



## 5. Weryfikacja (odznacz po kolei)



### Toolchain (host)

```bash
cd backend
uv run ruff check app
uv run ruff format --check app
cd ..
```

Oczekiwane: exit code `0`, bez findings.

### Backend

```bash
curl -s http://localhost:8000/health
```

Oczekiwane: `{"status":"ok"}`

Dokumentacja OpenAPI (sanity check, że FastAPI wstał):

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs
```

Oczekiwane: `200`

### Postgres

```bash
docker compose exec postgres pg_isready -U swarm -d swarm
```

Oczekiwane: `accepting connections`

```bash
docker compose exec postgres psql -U swarm -d swarm -c "SELECT 1 AS ok;"
```

Oczekiwane: wiersz z `1`.

### Redis

```bash
docker compose exec redis redis-cli ping
```

Oczekiwane: `PONG`

### Ollama (serwis żyje, bez modelu)

```bash
curl -s http://localhost:11434/api/tags
```

Oczekiwane: JSON z `"models":[]` albo listą (pusta jest OK).
Błąd połączenia = kontener nie nasłuchuje — patrz logi `docker compose logs ollama`.

### Compose health

```bash
docker compose ps
```

Kolumna `STATUS` powinna zawierać `healthy` dla `postgres`, `redis`, `backend`.
Ollama często nie ma healthchecka — wystarczy `Up`.

---



## 6. Typowe problemy


| Objaw                                       | Co sprawdzić                                                                                |
| ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `uv: command not found`                     | installer + `~/.local/bin` na `PATH`, nowy terminal                                         |
| `Unable to find lockfile` / `--locked` fail | nie pominąłeś `cd backend && uv lock`; `uv.lock` musi być w kontekście builda (`./backend`) |
| `port is already allocated`                 | `ss -tlnp                                                                                   |
| backend `unhealthy`                         | `docker compose logs backend` — składnia, zły `CMD`, albo `PATH` bez `.venv`                |
| `pg_isready` fail                           | poczekaj 10–20 s; Alpine potrzebuje chwili na init volume                                   |
| compose nie widzi `.env`                    | komendy odpalasz z katalogu, w którym leży `docker-compose.yml`                             |
| Ollama długo „wisi” na pull                 | **nie pulluj modelu**. Jeśli w logach jest `pulling`, przerwałeś zakres Dnia 1              |
| `permission denied` na sockecie Docker      | user w grupie `docker`, potem nowe logowanie                                                |
| Ruff krzyczy na I001 (importy)              | `uv run ruff check --fix app`                                                               |


Zatrzymanie bez kasowania danych:

```bash
docker compose down
```

Kasowanie volumes (niszczy lokalną bazę — dziś i tak pustą):

```bash
docker compose down -v
```

---



## 7. Co commitujesz po Dniu 1

Do gita:

- `docker-compose.yml`
- `.env.example` (nie `.env`)
- `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock`, `backend/.python-version`, `backend/.dockerignore`, `backend/app/**`
- `agents/.gitkeep`, `shared/.gitkeep`, `frontend/.gitkeep`
- ten dokument

Nie commituj: `.env`, `backend/.venv`, volumes Dockera, `__pycache__`, `.ruff_cache`.

Commit zrób dopiero gdy sam zdecydujesz — to nie jest automatyczny krok Dnia 1.

---



## 8. Checklista zamknięcia dnia

- [ ] katalogi `backend/`, `frontend/`, `agents/`, `shared/` istnieją
- [x] `backend/uv.lock` istnieje i powstał przez `uv lock` (nie ręcznie)
- [x] `uv run ruff check app` i `uv run ruff format --check app` są czyste
- [x] `GET /health` działa z hosta (Compose)
- [x] Postgres `SELECT 1` działa
- [x] Redis `PING` → `PONG`
- [x] Ollama `/api/tags` odpowiada
- [x] w repo **nie ma** `requirements.txt` ani `pip install`
- [x] w kodzie nie ma LangChain, Celery, SQLAlchemy, agentów

Gdy wszystkie checkboxy są zaznaczone, Faza 0 jest skończona.

---



## 9. Co jest następne (nie dziś)

**Dni 2–3 — walking skeleton danych** (osobny dokument, gdy Dzień 1 jest zielony):

1. Celery worker jako piąty serwis w Compose (zależność w `pyproject.toml` + `uv lock`)
2. `POST /tasks` wrzuca job
3. worker generuje **jeden akapit** (Ollama *albo* stub `LLM_STUB=1`)
4. zapis do Postgres (`agent_tasks`)
5. `GET /tasks/{id}` zwraca wynik

Nowe paczki zawsze: wpis w `pyproject.toml` → `uv lock` → `uv sync` → rebuild obrazu. Ruff zostaje w grupie `dev`.

Dopiero potem Faza 1: prawdziwe tabele `affiliate_programs` i endpointy HITL.

Nie skacz do Research Agenta, dopóki ten cienki przepływ nie działa end-to-end.