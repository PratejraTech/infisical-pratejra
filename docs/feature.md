# LoadEnv Feature Documentation

## Overview

`LoadEnv` is a thin, universal wrapper around Infisical's Python SDK that provides a simplified interface for managing secrets with built-in caching, logging, and error handling. It abstracts away the complexity of the Infisical SDK while maintaining full functionality.

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
# or
pip install -e ".[dev]"
```

### From PyPI (when published)

```bash
pip install secrets-env
# or
uv pip install secrets-env
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

### Using Default Project and Environment

```python
import os
import asyncio
from secrets_env import LoadEnv

# Set defaults via environment variables
os.environ["INFISICAL_PROJECT_ID"] = "your-project-id"
os.environ["INFISICAL_ENVIRONMENT"] = "dev"

async def main():
    client = LoadEnv()
    
    # Uses defaults from environment
    secret = await client.get(key="API_KEY")
    print(secret.get_secret_value())

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

### Listing Secrets

```python
async def list_secrets():
    client = LoadEnv()
    
    # List all secrets (returns BaseSecret objects)
    secrets = await client.list_secrets(
        project="your-project-id",
        env="prod",
        recursive=True,  # Include nested paths
        tag_filters=["production", "critical"]
    )
    
    for secret in secrets:
        print(f"Secret: {secret.secret_key}")

asyncio.run(list_secrets())
```

### Creating Secrets

```python
async def create_secret():
    client = LoadEnv()
    
    result = await client.create_secret(
        secret_name="NEW_API_KEY",
        secret_value="secret_value_123",
        project="your-project-id",
        env="dev",
        path="/app",
        secret_comment="API key for external service",
        secret_reminder_repeat_days=30,
        secret_reminder_note="Rotate this key monthly"
    )
    
    print(f"Created secret: {result}")

asyncio.run(create_secret())
```

### Updating Secrets

```python
async def update_secret():
    client = LoadEnv()
    
    await client.update_secret(
        current_secret_name="EXISTING_SECRET",
        secret_value="new_secret_value",
        project="your-project-id",
        env="dev",
        new_secret_name="UPDATED_SECRET",  # Optional rename
        secret_comment="Updated comment"
    )
    
    print("Secret updated successfully")

asyncio.run(update_secret())
```

### Getting Full Secret Object

```python
async def get_secret_object():
    client = LoadEnv()
    
    # Get full BaseSecret object with all metadata
    secret = await client.secret_by_name(
        secret_name="DATABASE_URL",
        project="your-project-id",
        env="dev"
    )
    
    # Access all secret properties
    print(f"Key: {secret.secret_key}")
    print(f"Value: {secret.secret_value}")
    print(f"Path: {secret.secret_path}")

asyncio.run(get_secret_object())
```

### Credential Override

```python
async def use_different_credentials():
    client = LoadEnv()
    
    # Override credentials for a specific call
    secret = await client.get(
        key="SPECIAL_SECRET",
        project="other-project-id",
        client_id="override_client_id",
        client_secret="override_client_secret"
    )
    
    print(secret.get_secret_value())

asyncio.run(use_different_credentials())
```

## Caching

The `LoadEnv` class uses a TTL cache (Time-To-Live) with the following defaults:

- **Max Size**: 100 secrets
- **TTL**: 3600 seconds (1 hour)

Cache keys are generated based on:
- Project ID
- Environment
- Secret path
- Secret key name

The cache is automatically invalidated when secrets are created or updated.

## Error Handling

All methods raise exceptions when operations fail. Common scenarios:

- **Missing Project ID**: `ValueError` if project ID is not provided
- **SDK Errors**: Original exceptions from Infisical SDK are propagated
- **Authentication Failures**: Exceptions during client initialization

Example error handling:

```python
async def safe_get_secret():
    client = LoadEnv()
    
    try:
        secret = await client.get(
            key="MISSING_SECRET",
            project="project-id"
        )
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Failed to retrieve secret: {e}")

asyncio.run(safe_get_secret())
```

## Logging

The `LoadEnv` class uses loguru for comprehensive logging:

- **INFO**: Normal operations (initialization, secret retrieval)
- **SUCCESS**: Successful operations
- **DEBUG**: Cache hits
- **ERROR**: Failures and exceptions

Logs are automatically formatted and can be configured via loguru's standard configuration.

## Best Practices

1. **Reuse Client Instances**: Create one `LoadEnv` instance and reuse it
2. **Use Environment Variables**: Set defaults via environment variables for consistency
3. **Handle Errors**: Always wrap secret retrieval in try/except blocks
4. **Cache Awareness**: Be aware that cached values may be up to 1 hour old
5. **Type Safety**: Use type hints and SecretStr for better code safety

## API Reference

### LoadEnv Class

#### `__init__(machine_identity_client_id=None, machine_identity_client_secret=None, host="https://app.infisical.com")`

Initialize the LoadEnv client.

#### `async get(key, *, project=None, env="dev", path="", client_id=None, client_secret=None) -> SecretStr`

Retrieve a single secret by key.

#### `async get_all(project=None, env="dev", path="") -> Dict[str, SecretStr]`

Retrieve all secrets for a project/environment/path.

#### `async list_secrets(project=None, env="dev", path="", expand_secret_references=True, view_secret_value=True, recursive=False, include_imports=True, tag_filters=None) -> list`

List secrets with optional filtering.

#### `async create_secret(secret_name, secret_value, project=None, env="dev", path=None, secret_comment=None, skip_multiline_encoding=False, secret_reminder_repeat_days=None, secret_reminder_note=None) -> Dict[str, Any]`

Create a new secret.

#### `async update_secret(current_secret_name, secret_value=None, project=None, env="dev", path=None, new_secret_name=None, secret_comment=None, skip_multiline_encoding=False, secret_reminder_repeat_days=None, secret_reminder_note=None, secret_metadata=None, tags_ids=None) -> None`

Update an existing secret.

#### `async secret_by_name(secret_name, project=None, env="dev", path=None) -> BaseSecret`

Get a full BaseSecret object by name.

