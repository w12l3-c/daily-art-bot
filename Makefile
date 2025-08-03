# Name of the Docker image
IMAGE_NAME = daily-art-bot

.PHONY: all build run stop logs shell install-deps deploy backup restore

all: build

## Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

## Run the container (detached, restart on reboot/crash)
run: stop
	docker run -d \
	  --name $(IMAGE_NAME) \
	  --restart unless-stopped \
	  --env-file .env \
	  -v $(PWD)/badges:/app/badges \
	  -v $(PWD)/backup.json:/app/backup.json \
	  -v $(PWD)/bot.log:/app/bot.log \
	  $(IMAGE_NAME)

## Stop & remove existing container
stop:
	-docker stop $(IMAGE_NAME)
	-docker rm $(IMAGE_NAME)

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

## Create backup of bot data
backup:
	cp backup.json backup.json.$(shell date +%Y%m%d_%H%M%S) 2>/dev/null || true
	@echo "Backup created (if backup.json existed)"

## Deploy: build and run with backup
deploy: backup build run
	@echo "Deployment complete! Use 'make logs' to monitor."

## (Optional) Install Docker on your Raspberry Pi
install-deps:
	sudo apt-get update
	sudo apt-get install -y docker.io docker-compose
	sudo usermod -aG docker $${USER}
	@echo "Log out/in or reboot so your user is in the docker group."
