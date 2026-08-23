IMAGE ?= epos:local

dev:
	docker compose -f ./docker-compose.dev.yml up --remove-orphans
dev-update:
	docker compose -f ./docker-compose.dev.yml up --build -V --remove-orphans
build:
	docker build -t $(IMAGE) .
test:
	python3 -m pytest -q tests
smoke:
	IMAGE=$(IMAGE) ./scripts/smoke_test.sh
