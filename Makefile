COMPOSE ?= docker compose
SERVICE ?=
PROFILES ?=

.PHONY: up up-core up-ml up-profiles down build build-base build-core build-ml rebuild logs ps

up:
	$(COMPOSE) build base-python
	$(COMPOSE) up --build -d $(SERVICE)

up-profiles:
	$(COMPOSE) build base-python
	COMPOSE_PROFILES=$(PROFILES) $(COMPOSE) up --build -d $(SERVICE)

up-core:
	$(COMPOSE) build base-python
	COMPOSE_PROFILES=core $(COMPOSE) up --build -d $(SERVICE)

up-ml:
	$(COMPOSE) build base-python
	COMPOSE_PROFILES=core,ml $(COMPOSE) up --build -d $(SERVICE)

build:
	$(COMPOSE) build base-python
	$(COMPOSE) build $(SERVICE)

build-base:
	$(COMPOSE) build base-python

build-core:
	$(COMPOSE) build base-python
	COMPOSE_PROFILES=core $(COMPOSE) build $(SERVICE)

build-ml:
	$(COMPOSE) build base-python
	COMPOSE_PROFILES=core,ml $(COMPOSE) build $(SERVICE)

rebuild:
	$(COMPOSE) build base-python
	$(COMPOSE) up --build -d $(SERVICE)

logs:
	$(COMPOSE) logs -f $(SERVICE)

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps
