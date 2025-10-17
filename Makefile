COMPOSE ?= docker compose
SERVICE ?=

.PHONY: up down build rebuild logs ps

up:
$(COMPOSE) up --build -d $(SERVICE)

build:
$(COMPOSE) build $(SERVICE)

rebuild:
$(COMPOSE) up --build -d $(SERVICE)

logs:
$(COMPOSE) logs -f $(SERVICE)

down:
$(COMPOSE) down

ps:
$(COMPOSE) ps
