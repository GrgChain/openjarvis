.PHONY: build up down restart logs push

ROOT_DIR = ..
IMAGE_NAME = openjarvis:latest
COMPOSE_FILE = docker-compose_openjarvis.yml
REGISTRY = registry.cn-guangzhou.aliyuncs.com/jonluo
REMOTE_IMAGE = $(REGISTRY)/$(IMAGE_NAME)

build:
	cd $(ROOT_DIR) && docker build -f openjarvis/Dockerfile_openjarvis -t $(IMAGE_NAME) .

push: build
	docker tag $(IMAGE_NAME) $(REMOTE_IMAGE)
	docker push $(REMOTE_IMAGE)

up: build
	docker-compose -f $(COMPOSE_FILE) up -d

down:
	docker-compose -f $(COMPOSE_FILE) down

restart: down up

logs:
	docker-compose -f $(COMPOSE_FILE) logs -f
