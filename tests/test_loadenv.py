"""Comprehensive test suite for LoadEnv class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import SecretStr
from infisical_sdk import BaseSecret

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from secrets_env import LoadEnv, Environment


@pytest.fixture
def mock_sdk_client():
    """Create a mock Infisical SDK client."""
    client = MagicMock()
    client.secrets = MagicMock()
    return client


@pytest.fixture
def load_env(mock_sdk_client):
    """Create a LoadEnv instance with mocked SDK client."""
    with patch('secrets_env._SDK', return_value=mock_sdk_client):
        env = LoadEnv(
            machine_identity_client_id="test_client_id",
            machine_identity_client_secret="test_client_secret",
        )
        env.client = mock_sdk_client
        return env


@pytest.fixture
def mock_secret():
    """Create a mock secret object."""
    secret = MagicMock(spec=BaseSecret)
    secret.secret_key = "TEST_SECRET"
    secret.secret_value = "test_value_123"
    return secret


class TestLoadEnvInit:
    """Test LoadEnv initialization."""
    
    def test_init_with_credentials(self, mock_sdk_client):
        """Test initialization with provided credentials."""
        with patch('secrets_env._SDK', return_value=mock_sdk_client):
            env = LoadEnv(
                machine_identity_client_id="test_id",
                machine_identity_client_secret="test_secret",
            )
            assert env._default_client_id == "test_id"
            assert env._default_client_secret == "test_secret"
            assert env.client == mock_sdk_client
    
    @patch.dict('os.environ', {
        'INFISICAL_MACHINE_ID': 'env_client_id',
        'INFISICAL_SECRET_KEY': 'env_secret_key',
        'INFISICAL_PROJECT_ID': 'test_project',
        'INFISICAL_ENVIRONMENT': 'staging',
        'INFISICAL_SECRET_PATH': '/custom/path',
    })
    def test_init_from_env_vars(self, mock_sdk_client):
        """Test initialization from environment variables."""
        with patch('secrets_env._SDK', return_value=mock_sdk_client):
            env = LoadEnv()
            assert env._default_client_id == "env_client_id"
            assert env._default_client_secret == "env_secret_key"
            assert env.project_id == "test_project"
            assert env.environment_slug == "staging"
            assert env.secret_path == "/custom/path"
    
    def test_init_sdk_initialization_failure(self):
        """Test initialization failure when SDK client cannot be created."""
        with patch('secrets_env._SDK', side_effect=Exception("SDK init failed")):
            with pytest.raises(Exception, match="SDK init failed"):
                LoadEnv(
                    machine_identity_client_id="test_id",
                    machine_identity_client_secret="test_secret",
                )


class TestLoadEnvGet:
    """Test LoadEnv.get() method."""
    
    @pytest.mark.asyncio
    async def test_get_secret_cache_hit(self, load_env, mock_secret):
        """Test retrieving a secret from cache."""
        # Pre-populate cache
        cache_key = "test_project:dev::TEST_SECRET"
        load_env._cache[cache_key] = SecretStr("cached_value")
        
        result = await load_env.get("TEST_SECRET", project="test_project")
        
        assert result.get_secret_value() == "cached_value"
        # Should not call SDK
        load_env.client.secrets.get_secret_by_name.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_secret_cache_miss(self, load_env, mock_secret):
        """Test retrieving a secret from Infisical (cache miss)."""
        mock_secret.secret_value = "fresh_value"
        load_env.client.secrets.get_secret_by_name = AsyncMock(return_value=mock_secret)
        
        result = await load_env.get("TEST_SECRET", project="test_project", env="dev")
        
        assert result.get_secret_value() == "fresh_value"
        load_env.client.secrets.get_secret_by_name.assert_called_once()
        # Verify cache was populated
        cache_key = "test_project:dev::TEST_SECRET"
        assert cache_key in load_env._cache
    
    @pytest.mark.asyncio
    async def test_get_secret_with_path(self, load_env, mock_secret):
        """Test retrieving a secret with a custom path."""
        mock_secret.secret_value = "path_value"
        load_env.client.secrets.get_secret_by_name = AsyncMock(return_value=mock_secret)
        
        result = await load_env.get(
            "TEST_SECRET",
            project="test_project",
            env="staging",
            path="/custom/path",
        )
        
        assert result.get_secret_value() == "path_value"
        load_env.client.secrets.get_secret_by_name.assert_called_once_with(
            secret_name="TEST_SECRET",
            project_id="test_project",
            environment_slug="staging",
            secret_path="/custom/path",
        )
    
    @pytest.mark.asyncio
    async def test_get_secret_with_credential_override(self, load_env, mock_secret):
        """Test retrieving a secret with credential overrides."""
        mock_secret.secret_value = "override_value"
        mock_sdk_override = MagicMock()
        mock_sdk_override.secrets = MagicMock()
        mock_sdk_override.secrets.get_secret_by_name = AsyncMock(return_value=mock_secret)
        
        with patch('secrets_env._SDK', return_value=mock_sdk_override):
            result = await load_env.get(
                "TEST_SECRET",
                project="test_project",
                client_id="override_id",
                client_secret="override_secret",
            )
        
        assert result.get_secret_value() == "override_value"
    
    @pytest.mark.asyncio
    async def test_get_secret_missing_project_id(self, load_env):
        """Test error when project ID is missing."""
        load_env.project_id = None
        
        with pytest.raises(ValueError, match="Project ID must be provided"):
            await load_env.get("TEST_SECRET")
    
    @pytest.mark.asyncio
    async def test_get_secret_sdk_error(self, load_env):
        """Test error handling when SDK call fails."""
        load_env.client.secrets.get_secret_by_name = AsyncMock(
            side_effect=Exception("SDK error")
        )
        
        with pytest.raises(Exception, match="SDK error"):
            await load_env.get("TEST_SECRET", project="test_project")


class TestLoadEnvGetAll:
    """Test LoadEnv.get_all() method."""
    
    @pytest.mark.asyncio
    async def test_get_all_secrets(self, load_env):
        """Test retrieving all secrets."""
        mock_secret1 = MagicMock()
        mock_secret1.secret_key = "SECRET_1"
        mock_secret1.secret_value = "value_1"
        
        mock_secret2 = MagicMock()
        mock_secret2.secret_key = "SECRET_2"
        mock_secret2.secret_value = "value_2"
        
        load_env.client.secrets.list_secrets = AsyncMock(
            return_value=[mock_secret1, mock_secret2]
        )
        
        result = await load_env.get_all(project="test_project", env="dev")
        
        assert len(result) == 2
        assert result["SECRET_1"].get_secret_value() == "value_1"
        assert result["SECRET_2"].get_secret_value() == "value_2"
        load_env.client.secrets.list_secrets.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_empty_result(self, load_env):
        """Test retrieving all secrets when none exist."""
        load_env.client.secrets.list_secrets = AsyncMock(return_value=[])
        
        result = await load_env.get_all(project="test_project")
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_all_missing_project_id(self, load_env):
        """Test error when project ID is missing."""
        load_env.project_id = None
        
        with pytest.raises(ValueError, match="Project ID must be provided"):
            await load_env.get_all()


class TestLoadEnvListSecrets:
    """Test LoadEnv.list_secrets() method."""
    
    @pytest.mark.asyncio
    async def test_list_secrets(self, load_env):
        """Test listing secrets with default parameters."""
        mock_secrets = [MagicMock(), MagicMock()]
        load_env.client.secrets.list_secrets = AsyncMock(return_value=mock_secrets)
        
        result = await load_env.list_secrets(project="test_project")
        
        assert result == mock_secrets
        load_env.client.secrets.list_secrets.assert_called_once_with(
            project_id="test_project",
            environment_slug="dev",
            secret_path="/",
            expand_secret_references=True,
            view_secret_value=True,
            recursive=False,
            include_imports=True,
            tag_filters=[],
        )
    
    @pytest.mark.asyncio
    async def test_list_secrets_with_filters(self, load_env):
        """Test listing secrets with custom filters."""
        mock_secrets = [MagicMock()]
        load_env.client.secrets.list_secrets = AsyncMock(return_value=mock_secrets)
        
        result = await load_env.list_secrets(
            project="test_project",
            env="prod",
            path="/app",
            recursive=True,
            tag_filters=["tag1", "tag2"],
        )
        
        assert result == mock_secrets
        load_env.client.secrets.list_secrets.assert_called_once_with(
            project_id="test_project",
            environment_slug="prod",
            secret_path="/app",
            expand_secret_references=True,
            view_secret_value=True,
            recursive=True,
            include_imports=True,
            tag_filters=["tag1", "tag2"],
        )


class TestLoadEnvCreateSecret:
    """Test LoadEnv.create_secret() method."""
    
    @pytest.mark.asyncio
    async def test_create_secret(self, load_env):
        """Test creating a new secret."""
        mock_result = {"id": "secret_123", "name": "NEW_SECRET"}
        load_env.client.secrets.create_secret_by_name = AsyncMock(return_value=mock_result)
        
        # Pre-populate cache to test invalidation
        cache_key = "test_project:dev::OTHER_SECRET"
        load_env._cache[cache_key] = SecretStr("other_value")
        
        result = await load_env.create_secret(
            secret_name="NEW_SECRET",
            secret_value="new_value",
            project="test_project",
        )
        
        assert result == mock_result
        load_env.client.secrets.create_secret_by_name.assert_called_once()
        # Cache should be invalidated
        assert cache_key not in load_env._cache
    
    @pytest.mark.asyncio
    async def test_create_secret_with_options(self, load_env):
        """Test creating a secret with all options."""
        mock_result = {"id": "secret_456"}
        load_env.client.secrets.create_secret_by_name = AsyncMock(return_value=mock_result)
        
        result = await load_env.create_secret(
            secret_name="NEW_SECRET",
            secret_value="new_value",
            project="test_project",
            env="staging",
            path="/custom",
            secret_comment="Test comment",
            secret_reminder_repeat_days=30,
            secret_reminder_note="Test note",
        )
        
        assert result == mock_result
        call_args = load_env.client.secrets.create_secret_by_name.call_args
        assert call_args.kwargs["secret_name"] == "NEW_SECRET"
        assert call_args.kwargs["secret_value"] == "new_value"
        assert call_args.kwargs["environment_slug"] == "staging"


class TestLoadEnvUpdateSecret:
    """Test LoadEnv.update_secret() method."""
    
    @pytest.mark.asyncio
    async def test_update_secret(self, load_env):
        """Test updating an existing secret."""
        load_env.client.secrets.update_secret_by_name = AsyncMock()
        
        # Pre-populate cache
        cache_key = "test_project:dev::EXISTING_SECRET"
        load_env._cache[cache_key] = SecretStr("old_value")
        
        await load_env.update_secret(
            current_secret_name="EXISTING_SECRET",
            secret_value="new_value",
            project="test_project",
        )
        
        load_env.client.secrets.update_secret_by_name.assert_called_once()
        # Cache should be invalidated
        assert cache_key not in load_env._cache
    
    @pytest.mark.asyncio
    async def test_update_secret_rename(self, load_env):
        """Test updating a secret with a new name."""
        load_env.client.secrets.update_secret_by_name = AsyncMock()
        
        await load_env.update_secret(
            current_secret_name="OLD_NAME",
            new_secret_name="NEW_NAME",
            secret_value="updated_value",
            project="test_project",
        )
        
        call_args = load_env.client.secrets.update_secret_by_name.call_args
        assert call_args.kwargs["current_secret_name"] == "OLD_NAME"
        assert call_args.kwargs["new_secret_name"] == "NEW_NAME"
        assert call_args.kwargs["secret_value"] == "updated_value"


class TestLoadEnvSecretByName:
    """Test LoadEnv.secret_by_name() method."""
    
    @pytest.mark.asyncio
    async def test_secret_by_name(self, load_env, mock_secret):
        """Test retrieving a secret object by name."""
        load_env.client.secrets.get_secret_by_name = AsyncMock(return_value=mock_secret)
        
        result = await load_env.secret_by_name("TEST_SECRET", project="test_project")
        
        assert result == mock_secret
        load_env.client.secrets.get_secret_by_name.assert_called_once_with(
            secret_name="TEST_SECRET",
            project_id="test_project",
            environment_slug="dev",
            secret_path="/",
        )
    
    @pytest.mark.asyncio
    async def test_secret_by_name_error(self, load_env):
        """Test error handling when secret is not found."""
        load_env.client.secrets.get_secret_by_name = AsyncMock(
            side_effect=Exception("Secret not found")
        )
        
        with pytest.raises(Exception, match="Secret not found"):
            await load_env.secret_by_name("MISSING_SECRET", project="test_project")


class TestLoadEnvCache:
    """Test LoadEnv caching functionality."""
    
    def test_cache_key_generation(self, load_env):
        """Test cache key generation."""
        key = load_env._key("project1", "dev", "/path")
        assert key == "project1:dev:/path"
        
        key2 = load_env._key("project1", "dev", "")
        assert key2 == "project1:dev:"
    
    @pytest.mark.asyncio
    async def test_cache_ttl(self, load_env, mock_secret):
        """Test that cache respects TTL."""
        # This is a basic test - full TTL testing would require time manipulation
        mock_secret.secret_value = "value1"
        load_env.client.secrets.get_secret_by_name = AsyncMock(return_value=mock_secret)
        
        # First call - should fetch and cache
        result1 = await load_env.get("TEST_SECRET", project="test_project")
        assert result1.get_secret_value() == "value1"
        
        # Second call - should use cache
        result2 = await load_env.get("TEST_SECRET", project="test_project")
        assert result2.get_secret_value() == "value1"
        # Should only be called once
        assert load_env.client.secrets.get_secret_by_name.call_count == 1

