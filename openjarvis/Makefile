.PHONY: build up down restart logs

ROOT_DIR = ..
IMAGE_NAME = openjarvis:latest
COMPOSE_FILE = docker-compose_openjarvis.yml

build:
	cd $(ROOT_DIR) && docker build -f openjarvis/Dockerfile_openjarvis -t $(IMAGE_NAME) .

up:
	docker compose -f $(COMPOSE_FILE) up -d

down:
	docker compose -f $(COMPOSE_FILE) down

restart: down up

logs:
	docker compose -f $(COMPOSE_FILE) logs -f
