# QuackTool 🦆

A QuackVerse tool for automation, built on top of QuackCore.

## 🌟 Features

- Process media assets (images, videos, audio, documents)
- Support for multiple processing modes (optimize, transform, analyze, generate)
- Command-line interface for easy use
- Python API for integration into other applications
- Plugin interface for extending functionality

## 🚀 Getting Started

### Prerequisites

- Python 3.13 or higher
- QuackCore library

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/quacktool.git
cd quacktool

# Install the package using a modern package manager like uv
uv venv --python 3.13
source .venv/bin/activate
uv pip install -e .

# Or use the provided setup script
make setup
source setup.sh
```

### Using the CLI

The QuackTool CLI provides commands for processing assets:

```bash
# Process a single file
quacktool process image.jpg --output processed.webp --quality 85

# Process multiple files in batch mode
quacktool batch image1.jpg image2.png --output-dir ./processed --format webp
```

### Using the Python API

```python
from pathlib import Path
from quacktool import process_asset
from quacktool.models import AssetConfig, ProcessingOptions, ProcessingMode

# Configure the asset processing
config = AssetConfig(
    input_path=Path("image.jpg"),
    output_path=Path("processed.webp"),
    options=ProcessingOptions(
        mode=ProcessingMode.OPTIMIZE,
        quality=85,
        format="webp",
    ),
)

# Process the asset
result = process_asset(config)

if result.success:
    print(f"Processing successful: {result.output_path}")
    print(f"Metrics: {result.metrics}")
else:
    print(f"Processing failed: {result.error}")
```

## 🧩 Integration with QuackCore

QuackTool integrates with QuackCore through the plugin system:

```python
from quackcore.plugins import registry

# Get the QuackTool plugin
quacktool_plugin = registry.get_plugin("QuackTool")

# Process a file using the plugin
result = quacktool_plugin.process_file(
    file_path="image.jpg",
    output_path="processed.webp",
    options={
        "quality": 85,
        "format": "webp",
        "mode": "optimize",
    },
)

if result.success:
    print(f"Processing successful: {result.content}")
else:
    print(f"Processing failed: {result.error}")

## 🔧 Development

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/quacktool.git
cd quacktool

# Set up development environment
make setup
source setup.sh

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

### Project Structure

The project follows a standard Python package structure:

```
quacktool/
├── examples/               # Usage examples
├── src/
│   └── quacktool/          # Main package
│       ├── __init__.py     # Package initialization
│       ├── cli.py          # Command-line interface
│       ├── config.py       # Configuration management
│       ├── core.py         # Core functionality
│       ├── models.py       # Data models
│       ├── plugin.py       # QuackCore plugin interface
│       └── version.py      # Version information
├── tests/                  # Test suite
├── .gitignore              # Git ignore file
├── Makefile                # Makefile for common tasks
├── pyproject.toml          # Project metadata and dependencies
└── README.md               # Project documentation
```

### Adding New Features

1. Implement the feature in the appropriate module
2. Add tests to verify the functionality
3. Update documentation with the new feature
4. Run the test suite to ensure everything works

## 📚 Configuration

QuackTool uses QuackCore's configuration system. The default configuration is:

```yaml
custom:
  quacktool:
    default_quality: 80
    default_format: "webp"
    temp_dir: "./temp"
    output_dir: "./output"
    log_level: "INFO"
```

You can override this configuration by creating a `quack_config.yaml` file in your project directory or by setting environment variables:

```bash
export QUACK_QUACKTOOL__DEFAULT_QUALITY=90
export QUACK_QUACKTOOL__OUTPUT_DIR="/custom/output/path"
```

## 📋 Command Reference

### `quacktool process`

Process a single file with custom options.

```bash
quacktool process INPUT_FILE [OPTIONS]
```

Options:
- `--output`, `-o`: Output path
- `--mode`, `-m`: Processing mode (optimize, transform, analyze, generate)
- `--quality`, `-q`: Quality level (1-100)
- `--format`, `-f`: Output format
- `--width`: Output width
- `--height`: Output height
- `--type`: Asset type (image, video, audio, document)

### `quacktool batch`

Process multiple files with the same settings.

```bash
quacktool batch [INPUT_FILES...] [OPTIONS]
```

Options:
- `--output-dir`, `-o`: Output directory (required)
- `--mode`, `-m`: Processing mode (optimize, transform, analyze, generate)
- `--quality`, `-q`: Quality level (1-100)
- `--format`, `-f`: Output format

## 🔌 Extending QuackTool

You can extend QuackTool by implementing your own processing functions in `core.py` or by creating new commands in `cli.py`.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- QuackCore for providing the foundation infrastructure
- The QuackVerse ecosystem for inspiration and integration