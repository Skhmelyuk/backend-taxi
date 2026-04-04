#!/bin/bash
# Script for updating dependencies via Docker container

# Activate virtual environment
source venv/bin/activate

echo "Updating the build tools inside the container..."
docker compose exec api pip install --upgrade pip pip-tools

echo "Compiling base.in -> base.txt..."
docker compose exec api pip-compile requirements/base.in --output-file=requirements/base.txt --resolver=backtracking

echo "Compiling development.in -> development.txt..."
docker compose exec api pip-compile requirements/development.in --output-file=requirements/development.txt --resolver=backtracking

echo "Compiling production.in -> production.txt..."
docker compose exec api pip-compile requirements/production.in --output-file=requirements/production.txt --resolver=backtracking

echo "Installing updated dependencies into the container..."
docker compose exec api pip install -r requirements/development.txt

echo "We record the current state in requirements-frozen.txt..."
docker compose exec api pip freeze > requirements-frozen.txt

echo "All requirements have been successfully updated!"