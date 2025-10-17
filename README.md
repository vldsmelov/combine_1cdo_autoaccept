# Combined Legal Automation Platform

Этот репозиторий объединяет три сервисных модуля в единую платформу с общим HTTP-шлюзом. Исходный код сервисов поставляется отдельно — поместите его в каталог `services/` (см. ниже), после чего можно собирать и запускать весь стек через Docker Compose. Все запросы идут через прокси по адресу `http://localhost:8000`.

## Структура проекта

```
.
├── docker-compose.yml
├── Makefile
├── proxy/
│   ├── Dockerfile
│   └── nginx.conf
└── services/
    ├── contract_extractor/   # код сервиса извлечения полей
    ├── globas_syntetic/      # код сервиса проверки контрагентов
    └── legal_ai/             # код сервиса анализа документов
```

> **Важно.** Каталоги внутри `services/` не входят в репозиторий. Скопируйте туда соответствующие проекты (например, через `git submodule`, `git subtree` или просто копированием файлов). Внутри каждого каталога должен находиться `Dockerfile`, который собирает сервис и публикует его на порту, указанном в `docker-compose.yml`.

## Подготовка сервисов

1. Склонируйте или скопируйте код каждого модуля в подпапки `services/contract_extractor`, `services/globas_syntetic` и `services/legal_ai`.
2. Убедитесь, что в каждом модуле есть `Dockerfile` с экспонированием портов `8080`, `8090` и `8100` соответственно.
3. При необходимости адаптируйте существующие приложения, чтобы они отвечали на эндпоинты, которые проброшены через прокси (см. раздел «Примеры запросов»).

## Быстрый старт

1. Убедитесь, что установлены Docker и Docker Compose v2.
2. Запустите все сервисы одной командой:

   ```bash
   make up
   ```

   Команда построит Docker-образы и поднимет контейнеры в фоне.

3. Проверьте, что сервисы доступны через прокси (после копирования исходных модулей):

   * `POST http://localhost:8000/contract-extractor/check`
   * `POST http://localhost:8000/globas-syntetic/verify`
   * `POST http://localhost:8000/legal-ai/analyze`

4. Остановите всю платформу:

   ```bash
   make down
   ```

## Работа с отдельными сервисами

Для пересборки только одного сервиса используйте переменную `SERVICE` (каталоги с кодом должны быть добавлены заранее):

```bash
make rebuild SERVICE=contract-extractor
make rebuild SERVICE=globas-syntetic
make rebuild SERVICE=legal-ai
```

Посмотреть логи:

```bash
make logs SERVICE=proxy
```

## Примеры запросов

### Contract Extractor

```bash
curl -X POST http://localhost:8000/contract-extractor/check \
  -H "Content-Type: application/json" \
  -d '{"text": "Contract No. 42 between Alpha LLC and Beta LTD effective date 01/04/2024 total fee $10000."}'
```

### Globas Synthetic

```bash
curl -X POST http://localhost:8000/globas-syntetic/verify \
  -H "Content-Type: application/json" \
  -d '{"inn": "1234567890", "ogrn": "1234567890123", "name": "ООО Пример"}'
```

### Legal AI

```bash
curl -X POST http://localhost:8000/legal-ai/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The supplier may impose a penalty for late payments. The buyer has no unilateral termination rights."}'
```

## Дополнительно

* В `docker-compose.yml` настроены healthcheck'и — убедитесь, что ваши сервисы реализуют эндпоинты `/health`.
* Внешние порты `18080`, `18090`, `18100` открыты для диагностики и обхода прокси при необходимости.

