# Combined Legal Automation Platform

Этот репозиторий объединяет четыре независимых сервиса — извлечение данных из договоров, проверку контрагентов, ИИ-юриста и ИИ-экономиста — в единую демо-платформу. Все сервисы работают в отдельных Docker-контейнерах, а вызовы идут через единый HTTP-шлюз `http://localhost:8000`.

## Структура проекта

```
.
├── docker-compose.yml        # единый стек
├── Makefile                  # удобные команды docker compose
├── proxy/
│   ├── Dockerfile            # Nginx как API-шлюз
│   └── nginx.conf
└── services/
    ├── contract-extractor/   # сервис извлечения полей
    ├── globas/               # сервис проверки контрагентов
    ├── legal_ai_1C/          # ИИ-юрист + его зависимости
    └── ai-economist/         # контроль бюджета и закупок
```

Каждый сервис поставляется отдельно. Просто скопируйте/склонируйте код в соответствующую подпапку `services/`. В каталогах уже лежат актуальные Dockerfile'ы из исходных проектов.

## Порты и точки входа

| Сервис                | Прокси-URL                         | Прямой порт (host) | Описание |
|-----------------------|------------------------------------|--------------------|----------|
| Contract Extractor    | `http://localhost:8000/contract-extractor/*` | `18080 → 8080`     | FastAPI-приложение для извлечения полей |
| Globas API            | `http://localhost:8000/globas/*`   | `18090 → 8000`     | FastAPI + PostgreSQL (`25432 → 5432`) |
| Legal AI API          | `http://localhost:8000/legal-ai/*` | `18100 → 8000`     | FastAPI, использует Ollama (`21434 → 11434`) и Qdrant (`26333 → 6333`, `26334 → 6334`) |
| AI Economist          | `http://localhost:8000/ai-economist/*` | `18110 → 8000`     | FastAPI, сопоставление закупок с бюджетом |

> Все сервисы также доступны напрямую по проброшенным портам для отладки. Nginx проксирует запросы, обрезая префикс (`/contract-extractor`, `/globas`, `/legal-ai`).

## Быстрый старт

1. Убедитесь, что установлены Docker и Docker Compose v2.
2. В корне репозитория выполните:

   ```bash
   make up
   ```

   Команда соберёт образы (включая тяжёлые слои Legal AI) и поднимет контейнеры в фоне.

3. Проверить готовность можно по health-check'ам или пробным запросам:

   ```bash
  curl http://localhost:8000/contract-extractor/health
  curl http://localhost:8000/globas/health
  curl http://localhost:8000/legal-ai/health
  curl http://localhost:8000/ai-economist/health
   ```

   ⚠️ Запуск Legal AI займёт несколько минут: контейнер скачивает веса моделей Ollama и Qdrant-кластеру требуется инициализация.

4. Остановить стек:

   ```bash
   make down
   ```

## Примеры запросов

```bash
# Contract Extractor
curl -X POST http://localhost:8000/contract-extractor/check \
  -H "Content-Type: application/json" \
  -d '{"text": "Contract No. 42 between Alpha LLC and Beta LTD effective date 01/04/2024 total fee $10000."}'

# Globas (пример проверки контрагента)
curl -X POST http://localhost:8000/globas/verify \
  -H "Content-Type: application/json" \
  -d '{"inn": "1234567890", "ogrn": "1234567890123", "name": "ООО Пример"}'

# Legal AI (анализ документа)
curl -X POST http://localhost:8000/legal-ai/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The supplier may impose a penalty for late payments. The buyer has no unilateral termination rights."}'

# AI Economist (проверка закупок)
curl -X POST http://localhost:8000/ai-economist/analyze \
  -H "Content-Type: application/json" \
  -d '{
        "budget_id": "demo",
        "items": [
          {"name": "Поставка МФУ Canon", "amount": "750 000"},
          {"name": "Сервер Lenovo", "amount": "1 200 000"}
        ]
      }'
```

## Документация

* [Архитектура сервисов](docs/architecture.md) — обзор общих принципов.
* [Contract Extractor](docs/contract_extractor.md) — подробности по сервису извлечения.
* [Globas API](docs/globas.md) — описание проверки контрагентов.
* [Legal AI Backend](docs/legal_ai.md) — сведения о сервисе юридического анализа.
* [AI Economist](docs/ai_economist.md) — сервис экономического контроля бюджета.

## Работа с отдельными сервисами

Команды Makefile проксируют аргументы в `docker compose` и позволяют управлять отдельными контейнерами:

```bash
# пересобрать и перезапустить только выбранный сервис
make rebuild SERVICE=contract-extractor
make rebuild SERVICE=globas-api
make rebuild SERVICE=legal-ai
make rebuild SERVICE=ai-economist

# посмотреть логи
make logs SERVICE=legal-ai
```

Имена сервисов совпадают с именами в `docker-compose.yml`, поэтому можно запускать `make up SERVICE=globas-api` или `docker compose up globas-db` — зависимости будут запущены автоматически.

## Обновление сервисов

1. Обновите код нужного модуля в `services/<name>` (git submodule, `git pull`, копирование файлов — любым удобным способом).
2. Выполните `make build SERVICE=<service>` или `make up SERVICE=<service>` — Docker пересоберёт образ только для этого сервиса.
3. При необходимости перезапустите прокси (`make up SERVICE=proxy`) — конфигурация Nginx обновляется через пересборку образа.

## Полезно знать

* Health-checkи ожидают, что сервисы отвечают на `/health`.
* Каталоги `legal_ai_ollama` и `legal_ai_qdrant` примонтированы как Docker volume — модели и данные сохраняются между перезапусками.
* При желании можно обращаться к сервисам напрямую, минуя прокси, например `http://localhost:18090/health`.
* Legal AI и Contract Extractor собираются с PyTorch nightly `cu130` и по умолчанию запускаются на GPU (Blackwell/RTX 5090). Убедитесь, что установлен NVIDIA Container Toolkit; при необходимости можно переключиться на CPU через переменные окружения.
