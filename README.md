# QuackMetadata

A QuackTool for extracting structured metadata from text documents using large language models.

## 🔍 Features

- Download text documents from Google Drive
- Extract structured metadata using LLMs (like GPT-4 or Claude)
- Validate output against a Pydantic schema
- Store results as `.metadata.json` files
- Upload metadata back to Google Drive
- Display metadata as trading cards in the terminal

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/quacktool.git
cd quackmetadata

# Install with development dependencies
pip install -e ".[dev]"
```

## ⚙️ Configuration

Create a `quack_config.yaml` file in your working directory:

```yaml
general:
  project_name: QuackMetadata

integrations:
  google:
    client_secrets_file: config/google_client_secret.json
    credentials_file: config/google_credentials.json
    
  llm:
    default_provider: openai
    openai:
      api_key: YOUR_OPENAI_API_KEY
      default_model: gpt-4o
```

### Google Drive Setup

1. Create a Google Cloud Project and enable the Google Drive API
2. Create OAuth credentials (Desktop application)
3. Save the client secrets JSON file to `config/google_client_secret.json`
4. On first run, authenticate through your browser when prompted

### LLM Setup

1. Obtain an API key from OpenAI or Anthropic
2. Add it to your configuration file or set it as an environment variable:
   - `OPENAI_API_KEY` for OpenAI
   - `ANTHROPIC_API_KEY` for Anthropic

## 🚀 Usage

### Command-Line Interface

Extract metadata from a local text file:

```bash
quackmetadata metadata extract path/to/file.txt
```

Extract metadata from a Google Drive file (using file ID):

```bash
quackmetadata metadata extract 1abc2defg3hij
```

Additional options:

```bash
# Use a custom prompt template
quackmetadata metadata extract file.txt --prompt-template path/to/custom.mustache

# Don't upload results back to Google Drive
quackmetadata metadata extract file.txt --dry-run

# Specify an output path
quackmetadata metadata extract file.txt --output path/to/output.metadata.json

# Set number of retries for LLM calls
quackmetadata metadata extract file.txt --retries 5

# Enable verbose output
quackmetadata metadata extract file.txt --verbose
```

### Python API

```python
from quackmetadata.plugins.metadata import MetadataPlugin

# Create and initialize the plugin
plugin = MetadataPlugin()
plugin.initialize()

# Process a file
result = plugin.process_file(
   file_path="path/to/file.txt",
   output_path="path/to/output.metadata.json",
   options={
      "prompt_template": "path/to/custom.mustache",
      "retries": 3,
      "dry_run": False,
      "verbose": True
   }
)

if result.success:
   # Access the extracted metadata
   metadata = result.content.get("metadata")
   print(metadata)
else:
   print(f"Error: {result.error}")
```

## 📝 Metadata Schema

The extracted metadata follows this structure:

```python
class AuthorProfile(BaseModel):
    name: str                # Author's name
    profession: str          # Author's profession
    writing_style: str       # Writing style
    possible_age_range: str  # Estimated age range
    location_guess: str      # Possible location

class Metadata(BaseModel):
    title: str               # Document title
    summary: str             # Brief summary
    author_style: str        # Writing style
    tone: str                # Emotional tone
    language: str            # Document language
    domain: str              # Subject domain
    estimated_date: str | None = None  # Estimated date
    rarity: str              # Rarity classification
    author_profile: AuthorProfile  # Generated author profile
```

## 🎭 Customizing Prompts

Create custom prompt templates using Mustache syntax. Templates should be placed in the `prompts/metadata/` directory with a `.mustache` extension.

Available context variables:
- `{{content}}`: The document content

Example template:

```mustache
You are an assistant extracting metadata from a document.

Here is the content:
---
{{content}}
---

Extract the following fields:
- Title: ...
- Summary: ...
...
```

## 🖥️ Demo Output

When running the tool, you'll see a "metadata card" displayed in the terminal:

```
╔══════════════════════════════════════════╗
║            🃏 METADATA CARD              ║
╠══════════════════════════════════════════╣
║ Title: The Duck Rebellion               ║
║ Domain: Politics / Satire               ║
║ Tone: Ironic                            ║
║ Rarity: 🟣 Legendary                     ║
╚══════════════════════════════════════════╝
```

## 📄 License

GNU GPL

## 🧑‍🏫 Teaching Notes

QuackMetadata was created as a teaching tool to demonstrate:
- Prompt engineering
- Schema validation
- Integration of cloud services
- Good CLI/UX design
- Modularity and debugging