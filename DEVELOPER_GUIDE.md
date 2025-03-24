# 🛠️ QuackTool Developer Guide

Welcome to the QuackTool developer guide! This document provides detailed instructions for using and extending QuackTool, as well as for creating new QuackTools for the QuackVerse ecosystem.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Key Design Principles](#key-design-principles)
- [Implementation Details](#implementation-details)
- [Python 3.13 Best Practices](#python-313-best-practices)
- [How to Create a New QuackTool](#how-to-create-a-new-quacktool)
- [Integration with QuackBuddy](#integration-with-quackbuddy)
- [Testing Guidelines](#testing-guidelines)

## Architecture Overview

QuackTool follows a headless module architecture designed to be integrated with QuackBuddy. Key components include:

1. **Core Processing Logic** - The `process_asset()` function is the main entry point
2. **Pydantic Models** - Type-safe data structures with validation
3. **Plugin System** - Integration with QuackCore's plugin registry
4. **Configuration Management** - Integration with QuackCore's config system
5. **Demonstration CLI** - For testing and development only

## Key Design Principles

- **Headless First**: All functionality should be accessible programmatically without a CLI
- **Clean Public API**: Expose only what's necessary through `__init__.py`
- **Type Safety**: Use modern Python 3.13 type annotations throughout
- **Plugin-Based Discovery**: Allow tools to be discovered and used via QuackCore's plugin system
- **Comprehensive Testing**: Maintain high test coverage (>90%)

## Implementation Details

### Public API

The public API is deliberately minimal:

```python
# Import directly - this is how QuackBuddy would use QuackTool
from quacktool import process_asset, AssetConfig, ProcessingOptions
```

### Core Processing Function

```python
def process_asset(config: AssetConfig) -> ProcessingResult:
    """
    Process an asset based on the provided configuration.
    
    Args:
        config: Configuration for the asset to process
        
    Returns:
        ProcessingResult containing the result of the processing operation
    """
    # implementation...
```

### Plugin Registration

QuackTool registers a plugin with QuackCore:

```python
# In pyproject.toml
[project.entry-points."quackcore.plugins"]
quacktool = "quacktool.plugin:create_plugin"
```

## Python 3.13 Best Practices

QuackTool adopts Python 3.13 best practices:

1. **Modern Type Annotations**:
   - Use `|` for unions: `str | None` instead of `Optional[str]`
   - Use built-in collection types: `dict[str, int]` instead of `Dict[str, int]`
   - Use `collections.abc` for abstract types

2. **Explicit Type Annotations**:
   - Annotate all function parameters and return types
   - Make None types explicit with the pipe operator

3. **Pydantic Models**:
   - Use Pydantic for data validation and serialization
   - Use `Field` for model documentation and validation

## How to Create a New QuackTool

To create a new QuackTool:

1. **Clone this Repository**:
   ```bash
   git clone https://github.com/yourusername/quacktool.git my-quacktool
   cd my-quacktool
   ```

2. **Rename the Package**:
   - Rename `src/quacktool` to `src/myquacktool`
   - Update imports and references in all files
   - Update `pyproject.toml` with your package name

3. **Implement Core Logic**:
   - Modify `core.py` with your processing logic
   - Update or extend the models in `models.py` as needed
   - Customize the configuration in `config.py`

4. **Register the Plugin**:
   - Update the plugin name in `plugin.py`
   - Update the entry point in `pyproject.toml`

5. **Write Tests**:
   - Test both public API and plugin interface
   - Achieve >90% test coverage

## Integration with QuackBuddy

QuackBuddy will use your tool in one of two ways:

### Method 1: Direct API Import

```python
from myquacktool import process_asset, AssetConfig, ProcessingOptions

result = process_asset(AssetConfig(
    input_path=Path("file.txt"),
    options=ProcessingOptions(mode="optimize"),
))
```

### Method 2: Plugin Registry

```python
from quackcore.plugins import registry

plugin = registry.get_plugin("MyQuackTool")
if plugin and plugin.is_available():
    result = plugin.process_file(
        file_path="file.txt",
        options={"mode": "optimize"}
    )
```

## Testing Guidelines

1. **Test Direct API Usage**:
   ```python
   # tests/test_headless_api.py
   from myquacktool import process_asset
   from myquacktool.models import AssetConfig
   
   def test_headless_api():
       result = process_asset(AssetConfig(...))
       assert result.success
   ```

2. **Test Plugin Interface**:
   ```python
   # tests/test_plugin.py
   from myquacktool.plugin import create_plugin
   
   def test_plugin():
       plugin = create_plugin()
       result = plugin.process_file(...)
       assert result.success
   ```

3. **Test Core Logic**:
   ```python
   # tests/test_core.py
   from myquacktool.core import process_asset
   
   def test_core_logic():
       # Test specific processing logic
   ```

---

## Remember

- QuackTools are meant to be headless; the CLI is for testing only
- QuackBuddy is the central user interface for the QuackVerse ecosystem
- Clear separation of concerns makes for a maintainable codebase
- Python 3.13 type annotations help catch errors early

Happy QuackTooling! 🦆