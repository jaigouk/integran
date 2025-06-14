# Test Structure

This directory contains all tests for the Integran project, organized to mirror the source code structure and support different types of testing.

## Directory Structure

```
tests/
├── conftest.py         # Shared pytest configuration and fixtures
├── unit/               # Unit tests for individual modules
│   ├── core/           # Core functionality tests
│   ├── cli/            # Command-line interface tests  
│   ├── ui/             # Terminal UI component tests
│   └── utils/          # Utility function tests
├── integration/        # End-to-end integration tests
└── test_*.py           # Main application tests
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