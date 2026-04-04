# Requirements

This directory contains Python package requirements for different environments.

## Files

- **base.txt** - Core dependencies required for all environments
- **development.txt** - Development tools, testing, and debugging packages
- **production.txt** - Production server and monitoring packages
- **test.txt** - Testing-specific packages

## Installation

### Development Environment

```bash
pip install -r requirements/development.txt
```

### Production Environment

```bash
pip install -r requirements/production.txt
```

### Testing Environment

```bash
pip install -r requirements/test.txt
```

## Installation (Docker-way)

For development we use the `api` container. To install or update packages without rebuilding the image:

```bash
docker compose exec api pip install -r requirements/development.txt
```

## Updating Requirements

When adding new packages:

1. Add to appropriate requirements file (base, development, production, or test)
2. Install the package: `pip install package-name`
3. Update frozen requirements: `pip freeze > requirements-frozen.txt`
4. Commit changes to git


## Notes

- Always use virtual environment
- Pin major versions for stability
- Test compatibility before updating packages
- Keep requirements files synchronized