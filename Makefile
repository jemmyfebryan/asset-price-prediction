.PHONY: install start stop restart logs clean clean-pycache test

PROJECT_NAME = asset-price-prediction-backend
PM2_CONFIG = pm2.config.js

install:
	pip install --upgrade pip
	pip install -r requirements.txt

start:
	PYTHONPATH=. pm2 start $(PM2_CONFIG)

stop:
	pm2 stop $(PROJECT_NAME) || true

restart:
	PYTHONPATH=. pm2 restart $(PROJECT_NAME)

logs:
	pm2 logs $(PROJECT_NAME)

clean: stop clean-pycache

clean-pycache:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .mypy_cache

test:
	PYTHONPATH=. pytest
	make clean-pycache
