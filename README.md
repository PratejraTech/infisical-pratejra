# secrets-env

Universal wrapper around Infisical's Python SDK for secret management with built-in caching, logging, and error handling.

## Features

- **Automatic Caching**: TTL-based cache (1 hour default) to reduce API calls
- **Comprehensive Logging**: Built-in loguru logging for all operations
- **Environment Support**: Support for dev, staging, and prod environments
- **Flexible Configuration**: Supports environment variables or direct parameter passing
- **Full CRUD Operations**: Create, read, update, and list secrets
- **Async/Await Support**: All methods are async for better performance
- **Type Safety**: Full type hints and Pydantic integration

## Installation

### From Source

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .

# With dev dependencies for testing
uv pip install -e ".[dev]"
```

### From PyPI (when published)

```bash
pip install secrets-env
# or
uv pip install secrets-env
```

## Quick Start

```python
import asyncio
from secrets_env import LoadEnv

async def main():
    # Initialize client (uses environment variables by default)
    client = LoadEnv()
    
    # Get a secret
    secret = await client.get(
        key="DATABASE_URL",
        project="your-project-id",
        env="dev"
    )
    
    # Access the secret value
    db_url = secret.get_secret_value()
    print(f"Database URL: {db_url}")

asyncio.run(main())
```

## Configuration

### Environment Variables

The `LoadEnv` class can be configured via environment variables:

- `INFISICAL_MACHINE_ID`: Machine identity client ID
- `INFISICAL_SECRET_KEY`: Machine identity client secret
- `INFISICAL_PROJECT_ID`: Default project ID
- `INFISICAL_ENVIRONMENT`: Default environment (dev, staging, prod)
- `INFISICAL_SECRET_PATH`: Default secret path (default: "/")

### Direct Initialization

```python
from secrets_env import LoadEnv

# Initialize with credentials
client = LoadEnv(
    machine_identity_client_id="your_client_id",
    machine_identity_client_secret="your_client_secret",
    host="https://app.infisical.com"  # Optional, defaults to Infisical cloud
)
```

## Usage Examples

### Basic Secret Retrieval

```python
import asyncio
from secrets_env import LoadEnv

async def main():
    client = LoadEnv()
    
    # Get a single secret
    secret = await client.get(
        key="DATABASE_URL",
        project="your-project-id",
        env="dev"
    )
    
    # Access the secret value
    db_url = secret.get_secret_value()
    print(f"Database URL: {db_url}")

asyncio.run(main())
```

### Retrieving All Secrets

```python
async def get_all_secrets():
    client = LoadEnv()
    
    # Get all secrets for a project/environment
    secrets = await client.get_all(
        project="your-project-id",
        env="dev",
        path="/app"
    )
    
    # Iterate over secrets
    for key, value in secrets.items():
        print(f"{key}: {value.get_secret_value()}")

asyncio.run(get_all_secrets())
```

### Creating and Updating Secrets

```python
async def manage_secrets():
    client = LoadEnv()
    
    # Create a new secret
    await client.create_secret(
        secret_name="NEW_API_KEY",
        secret_value="secret_value_123",
        project="your-project-id",
        env="dev"
    )
    
    # Update an existing secret
    await client.update_secret(
        current_secret_name="EXISTING_SECRET",
        secret_value="new_secret_value",
        project="your-project-id",
        env="dev"
    )

asyncio.run(manage_secrets())
```

## API Reference

### LoadEnv Class

#### `__init__(machine_identity_client_id=None, machine_identity_client_secret=None, host="https://app.infisical.com")`

Initialize the LoadEnv client.

#### `async get(key, *, project=None, env="dev", path="", client_id=None, client_secret=None) -> SecretStr`

Retrieve a single secret by key.

#### `async get_all(project=None, env="dev", path="") -> Dict[str, SecretStr]`

Retrieve all secrets for a project/environment/path.

#### `async list_secrets(project=None, env="dev", path="", ...) -> list`

List secrets with optional filtering.

#### `async create_secret(secret_name, secret_value, project=None, env="dev", ...) -> Dict[str, Any]`

Create a new secret.

#### `async update_secret(current_secret_name, secret_value=None, project=None, env="dev", ...) -> None`

Update an existing secret.

#### `async secret_by_name(secret_name, project=None, env="dev", path=None) -> BaseSecret`

Get a full BaseSecret object by name.

## Documentation

For detailed documentation, see:
- [Feature Documentation](docs/feature.md)
- [Integration Summary](docs/infisical-client.mdx)

## Requirements

- Python >= 3.10
- infisicalsdk >= 1.0.12
- loguru >= 0.7.3
- pydantic >= 2.12.4
- python-dotenv >= 1.2.1
- cachetools >= 5.3.3

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]

