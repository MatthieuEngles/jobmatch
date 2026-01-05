# Installing the jobmatch-shared Package

This document explains how to install the `jobmatch-shared` package with its dependencies.

## Installation Methods

### Option 1: Install in editable mode (Development)

```bash
# Navigate to the shared directory
cd shared

# Install with basic dependencies only
pip install -e .

# Install with embeddings support (includes sentence-transformers)
pip install -e ".[embeddings]"

# Install with dev dependencies (includes pytest)
pip install -e ".[dev]"

# Install with all optional dependencies
pip install -e ".[embeddings,dev]"
```

### Option 2: Install from parent directory

```bash
# From the jobmatch root directory
pip install -e ./shared

# With embeddings support
pip install -e "./shared[embeddings]"
```

## Setting Up a Python Virtual Environment

### Using venv (Python built-in)

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install the shared package
pip install -e "shared[embeddings,dev]"

# Deactivate when done
deactivate
```

### Using pyenv with virtualenv

```bash
# Install Python 3.12 if not already installed
pyenv install 3.12

# Create a virtual environment for the project
pyenv virtualenv 3.12 jobmatch-env

# Activate the environment
pyenv activate jobmatch-env

# Install the shared package
pip install -e "shared[embeddings,dev]"

# Deactivate when done
pyenv deactivate
```

### Using poetry (Alternative)

If you prefer using Poetry, you can convert the `pyproject.toml`:

```bash
# Install poetry if not already installed
pip install poetry

# Navigate to shared directory
cd shared

# Install dependencies
poetry install

# Install with optional dependencies
poetry install --extras "embeddings dev"

# Activate the poetry shell
poetry shell
```

## Dependencies Breakdown

### Core Dependencies (always installed)
- **pydantic** (>=2.0.0): Data validation and serialization
- **numpy** (>=1.24.0): Numerical computing (required for embeddings)

### Optional Dependencies

#### Embeddings Extra
- **sentence-transformers** (>=2.0.0): Sentence embeddings model
- **vec2vec** (>=0.0.5): Alternative embeddings provider

#### Dev Extra
- **pytest** (>=8.0.0): Testing framework

## Verifying Installation

After installation, verify that the package is correctly installed:

```bash
# Test import
python -c "from shared.embeddings import create_embedder; print('✓ Import successful')"

# Test with sentence-transformers (if embeddings extra was installed)
python -c "from shared.embeddings import create_embedder; embedder = create_embedder('sentence_transformers'); print('✓ Embedder created successfully')"
```

## Troubleshooting

### Import Error: "No module named 'numpy'"

**Solution**: `numpy` is now included in core dependencies. Reinstall:
```bash
pip install -e .
```

### Import Error: "No module named 'sentence_transformers'"

**Solution**: Install with embeddings support:
```bash
pip install -e ".[embeddings]"
```

### Docker Installation

The shared package is automatically installed in Docker containers via the Dockerfile:

```dockerfile
# Copy shared package and install
COPY shared /app/shared
RUN pip install -e /app/shared
```

For containers that need embeddings:
```dockerfile
RUN pip install -e "/app/shared[embeddings]"
```
