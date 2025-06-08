# Test Structure

This directory contains all tests for the Integran project, organized to mirror the source code structure and support different types of testing.

## Directory Structure

```
tests/
├── README.md           # This file
├── conftest.py         # Shared pytest configuration and fixtures
├── __init__.py         # Makes tests a Python package
├── unit/               # Unit tests organized by source module
│   ├── __init__.py
│   ├── core/           # Tests for src/core/
│   │   ├── __init__.py
│   │   ├── test_database.py     # Tests for src/core/database.py
│   │   ├── test_models.py       # Tests for src/core/models.py
│   │   └── test_settings.py     # Tests for src/core/settings.py
│   ├── cli/            # Tests for src/cli/
│   │   ├── __init__.py
│   │   ├── test_cli_build_knowledge_base.py   # Tests for src/cli/build_knowledge_base.py
│   │   └── test_cli_generate_explanations.py  # Tests for src/cli/generate_explanations.py
│   ├── knowledge_base/ # Tests for src/knowledge_base/
│   │   ├── __init__.py
│   │   ├── test_content_fetcher.py    # Tests for src/knowledge_base/content_fetcher.py
│   │   ├── test_rag_engine.py         # Tests for src/knowledge_base/rag_engine.py
│   │   ├── test_text_splitter.py      # Tests for src/knowledge_base/text_splitter.py
│   │   └── test_vector_store.py       # Tests for src/knowledge_base/vector_store.py
│   └── utils/          # Tests for src/utils/
│       ├── __init__.py
│       ├── test_explanation_generator.py  # Tests for src/utils/explanation_generator.py
│       ├── test_gemini_client.py          # Tests for src/utils/gemini_client.py
│       └── test_pdf_extractor.py          # Tests for src/utils/pdf_extractor.py
├── integration/        # Integration tests (future)
│   └── __init__.py
├── test_setup.py       # Tests for src/setup.py (root level module)
└── test_trainer.py     # Tests for src/trainer.py (root level module)
```

## Test Types

### Unit Tests (`tests/unit/`)
- Tests for individual modules and functions
- Each test file corresponds directly to a source file
- Should use mocking to isolate the unit under test
- Fast execution, no external dependencies

### Integration Tests (`tests/integration/`)
- Tests that verify multiple components work together
- May include end-to-end scenarios
- Can test with real external services (with proper isolation)
- Examples (to be added):
  - `test_cli_integration.py` - Full CLI command workflows
  - `test_rag_pipeline.py` - Complete RAG pipeline from content fetching to explanation generation
  - `test_training_flow.py` - Complete training workflow with database interactions

### Root Level Tests
- Tests for main entry point modules (`setup.py`, `trainer.py`)
- These remain at the root level as they represent the main application entry points

## Running Tests

### All Tests
```bash
pytest
# or
make test
```

### Unit Tests Only
```bash
pytest tests/unit/
```

### Specific Module Tests
```bash
pytest tests/unit/core/         # All core module tests
pytest tests/unit/cli/          # All CLI tests
pytest tests/unit/knowledge_base/  # All knowledge base tests
pytest tests/unit/utils/        # All utils tests
```

### Integration Tests Only
```bash
pytest tests/integration/
```

### Specific Test File
```bash
pytest tests/unit/core/test_database.py
pytest tests/unit/cli/test_cli_build_knowledge_base.py
```

### With Coverage
```bash
pytest --cov=src tests/
```

## Benefits of This Structure

1. **Clear Mapping**: Easy to find tests for any source file
2. **Maintainability**: Changes to source structure can be reflected in test structure
3. **Scalability**: Easy to add new test types (e.g., performance tests, security tests)
4. **IDE Support**: Better navigation and organization in IDEs
5. **Selective Testing**: Can run tests for specific modules or types
6. **Future-Ready**: Prepared for integration tests and other test types

## Naming Conventions

- Unit test files: `test_{module_name}.py`
- Integration test files: `test_{feature_name}_integration.py`
- Test classes: `TestModuleName` or `TestFeatureName`
- Test methods: `test_{specific_functionality}`