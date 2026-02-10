# Installation Guide

## Quick Start

### Option 1: Using pip (Recommended for users)
```bash
pip install -r requirements.txt
```

### Option 2: Using pyproject.toml (Recommended for developers)
```bash
# Install in editable mode with dev dependencies
pip install -e .[dev]

# Or just the package
pip install -e .
```

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/deterministic-walkers.git
   cd deterministic-walkers
   ```

2. **Create a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   # Development install (recommended)
   pip install -e .[dev]

   # Or minimal install
   pip install -r requirements.txt
   ```

4. **Verify installation**
   ```bash
   python -c "from generator.dialogue import DialogueGenerator; print('✅ Installation successful!')"
   ```

## Optional Dependencies

### LLM Providers (optional)
If you want to use alternative LLM providers:
```bash
pip install -e .[llm]
```

## Running Tests
```bash
pytest tests/
```

## Code Quality Tools
```bash
# Format code
black generator/ tools/ judge/ qa/

# Sort imports
isort generator/ tools/ judge/ qa/

# Lint
ruff check generator/ --fix

# Type check
mypy generator/
```
