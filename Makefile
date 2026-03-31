# Name of the Docker image
IMAGE_NAME = daily-art-bot

.PHONY: all build run stop logs shell install-deps deploy backup restore redeploy

all: build

## Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

## Run the container (detached, restart on reboot/crash)
run: stop
	@echo "Creating required files if they don't exist..."
	@mkdir -p badges
	@if [ ! -f backup.json ]; then \
		echo "Warning: backup.json doesn't exist, creating empty one..."; \
		echo '{}' > backup.json; \
	else \
		echo "Using existing backup.json"; \
	fi
	@test -f bot.log || touch bot.log
	docker run -d \
	  --name $(IMAGE_NAME) \
	  --restart unless-stopped \
	  --env-file .env \
	  -v $(PWD):/app \
	  $(IMAGE_NAME)

## Stop & remove existing container
stop:
	-docker stop $(IMAGE_NAME)
	-docker rm $(IMAGE_NAME)
	@bash ./auto_backup.sh

## Tail the bot logs
logs:
	docker logs -f $(IMAGE_NAME)

## View bot log file
logs-file:
	tail -f bot.log

## Open a shell inside the running container
shell:
	docker exec -it $(IMAGE_NAME) /bin/bash

## Check if container is running
status:
	docker ps | grep $(IMAGE_NAME) || echo "Container not running"

## Setup: Create required files and directories
setup:
	@echo "Setting up required files and directories..."
	@mkdir -p badges
	@if [ ! -f backup.json ]; then \
		echo "Creating initial backup.json..."; \
		echo '{}' > backup.json; \
	else \
		echo "backup.json already exists, preserving it."; \
	fi
	@test -f bot.log || touch bot.log
	@test -f .env || cp .env.example .env
	@echo "Setup complete! Make sure to edit .env with your bot token."

## Create backup of bot data
backup:
	cp backup.json backup.json.$(shell date +%Y%m%d_%H%M%S) 2>/dev/null || true
	@echo "Backup created (if backup.json existed)"

## Deploy: setup, build and run with backup
deploy: setup backup build run
	@echo "Deployment complete! Use 'make logs' to monitor."

## Redeploy: stop, pull latest, and deploy
redeploy:
	$(MAKE) stop
	git pull
	$(MAKE) deploy

## (Optional) Install Docker on your Raspberry Pi
install-deps:
	sudo apt-get update
	sudo apt-get install -y docker.io docker-compose
	sudo usermod -aG docker $${USER}
	@echo "Log out/in or reboot so your user is in the docker group."
