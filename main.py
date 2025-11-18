"""Thin wrapper around Infisical's Python SDK for universal secret management."""

import os
from typing import Dict, Any, Literal, Optional
from cachetools import TTLCache
from pydantic import BaseModel, SecretStr, Field
from loguru import logger
from infisical_sdk import InfisicalSDKClient as _SDK, BaseSecret
from dotenv import load_dotenv

load_dotenv()

Environment = Literal["dev", "staging", "prod"]


class InfisicalSecrets(BaseModel):
    """Pydantic model for Infisical machine identity credentials."""
    
    machine_identity_client_id: str = Field(
        default_factory=lambda: os.getenv("INFISICAL_MACHINE_ID", "")
    )
    machine_identity_client_secret: str = Field(
        default_factory=lambda: os.getenv("INFISICAL_SECRET_KEY", "")
    )


class LoadEnv:
    """Universal wrapper for Infisical SDK with caching and logging support."""
    
    def __init__(
        self,
        machine_identity_client_id: Optional[str] = None,
        machine_identity_client_secret: Optional[str] = None,
        host: str = "https://app.infisical.com",
    ) -> None:
        """
        Initialize the LoadEnv client.
        
        Args:
            machine_identity_client_id: Infisical machine identity client ID
            machine_identity_client_secret: Infisical machine identity client secret
            host: Infisical host URL (default: https://app.infisical.com)
        """
        logger.info("Initializing LoadEnv client")
        
        self._cache = TTLCache(maxsize=100, ttl=3600)
        self._default_client_id = (
            machine_identity_client_id
            or os.getenv("INFISICAL_MACHINE_ID", "")
        )
        self._default_client_secret = (
            machine_identity_client_secret
            or os.getenv("INFISICAL_SECRET_KEY", "")
        )
        
        self.project_id = os.getenv("INFISICAL_PROJECT_ID")
        self.environment_slug = os.getenv("INFISICAL_ENVIRONMENT", "dev")
        self.secret_path = os.getenv("INFISICAL_SECRET_PATH", "/")
        
        # Initialize the SDK client
        try:
            self.client = _SDK(
                client_id=self._default_client_id,
                client_secret=self._default_client_secret,
                host=host,
            )
            logger.success("Infisical SDK client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Infisical SDK client: {e}")
            raise
    
    def _key(self, project_id: str, environment: str, path: str = "") -> str:
        """Generate cache key from project, environment, and path."""
        return f"{project_id}:{environment}:{path}"
    
    async def get(
        self,
        key: str,
        *,
        project: Optional[str] = None,
        env: Environment = "dev",
        path: str = "",
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> SecretStr:
        """
        Retrieve a secret by key with caching support.
        
        Args:
            key: Secret key name
            project: Project ID (uses default if not provided)
            env: Environment (dev, staging, prod)
            path: Secret path
            client_id: Optional client ID override
            client_secret: Optional client secret override
            
        Returns:
            SecretStr containing the secret value
            
        Raises:
            Exception: If secret retrieval fails
        """
        project_id = project or self.project_id
        if not project_id:
            raise ValueError("Project ID must be provided or set via INFISICAL_PROJECT_ID")
        
        cache_key = f"{self._key(project_id, env, path)}:{key}"
        
        # Check cache first
        if cache_key in self._cache:
            logger.debug(f"Cache hit for secret: {key}")
            return self._cache[cache_key]
        
        logger.info(f"Fetching secret '{key}' from Infisical (project: {project_id}, env: {env})")
        
        try:
            # Create SDK instance if credentials are overridden
            if client_id or client_secret:
                sdk = _SDK(
                    client_id=client_id or self._default_client_id,
                    client_secret=client_secret or self._default_client_secret,
                )
            else:
                sdk = self.client
            
            # Fetch secret from Infisical
            secret = await sdk.secrets.get_secret_by_name(
                secret_name=key,
                project_id=project_id,
                environment_slug=env,
                secret_path=path or self.secret_path,
            )
            
            value = SecretStr(secret.secret_value)
            self._cache[cache_key] = value
            logger.success(f"Successfully retrieved secret: {key}")
            return value
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret '{key}': {e}")
            raise
    
    async def get_all(
        self,
        project: Optional[str] = None,
        env: Environment = "dev",
        path: str = "",
    ) -> Dict[str, SecretStr]:
        """
        Retrieve all secrets for a project/environment/path combination.
        
        Args:
            project: Project ID (uses default if not provided)
            env: Environment (dev, staging, prod)
            path: Secret path
            
        Returns:
            Dictionary mapping secret keys to SecretStr values
            
        Raises:
            Exception: If secret retrieval fails
        """
        project_id = project or self.project_id
        if not project_id:
            raise ValueError("Project ID must be provided or set via INFISICAL_PROJECT_ID")
        
        logger.info(f"Fetching all secrets (project: {project_id}, env: {env}, path: {path})")
        
        try:
            secrets_list = await self.client.secrets.list_secrets(
                project_id=project_id,
                environment_slug=env,
                secret_path=path or self.secret_path,
                expand_secret_references=True,
                view_secret_value=True,
                recursive=False,
                include_imports=True,
                tag_filters=[],
            )
            
            result = {}
            for secret in secrets_list:
                if hasattr(secret, 'secret_key') and hasattr(secret, 'secret_value'):
                    result[secret.secret_key] = SecretStr(secret.secret_value)
            
            logger.success(f"Successfully retrieved {len(result)} secrets")
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve secrets: {e}")
            raise
    
    async def list_secrets(
        self,
        project: Optional[str] = None,
        env: Environment = "dev",
        path: str = "",
        expand_secret_references: bool = True,
        view_secret_value: bool = True,
        recursive: bool = False,
        include_imports: bool = True,
        tag_filters: list = None,
    ) -> list:
        """
        List all secrets with optional filtering.
        
        Args:
            project: Project ID (uses default if not provided)
            env: Environment (dev, staging, prod)
            path: Secret path
            expand_secret_references: Whether to expand secret references
            view_secret_value: Whether to include secret values
            recursive: Whether to recursively list secrets
            include_imports: Whether to include imported secrets
            tag_filters: List of tag IDs to filter by
            
        Returns:
            List of BaseSecret objects
            
        Raises:
            Exception: If listing fails
        """
        project_id = project or self.project_id
        if not project_id:
            raise ValueError("Project ID must be provided or set via INFISICAL_PROJECT_ID")
        
        logger.info(f"Listing secrets (project: {project_id}, env: {env}, path: {path})")
        
        try:
            secrets = await self.client.secrets.list_secrets(
                project_id=project_id,
                environment_slug=env,
                secret_path=path or self.secret_path,
                expand_secret_references=expand_secret_references,
                view_secret_value=view_secret_value,
                recursive=recursive,
                include_imports=include_imports,
                tag_filters=tag_filters or [],
            )
            
            logger.success(f"Successfully listed {len(secrets)} secrets")
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            raise
    
    async def create_secret(
        self,
        secret_name: str,
        secret_value: str,
        project: Optional[str] = None,
        env: Environment = "dev",
        path: Optional[str] = None,
        secret_comment: Optional[str] = None,
        skip_multiline_encoding: bool = False,
        secret_reminder_repeat_days: Optional[int] = None,
        secret_reminder_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new secret in Infisical.
        
        Args:
            secret_name: Name of the secret
            secret_value: Value of the secret
            project: Project ID (uses default if not provided)
            env: Environment (dev, staging, prod)
            path: Secret path (uses default if not provided)
            secret_comment: Optional comment for the secret
            skip_multiline_encoding: Whether to skip multiline encoding
            secret_reminder_repeat_days: Days until reminder
            secret_reminder_note: Reminder note
            
        Returns:
            Dictionary containing the created secret information
            
        Raises:
            Exception: If secret creation fails
        """
        project_id = project or self.project_id
        if not project_id:
            raise ValueError("Project ID must be provided or set via INFISICAL_PROJECT_ID")
        
        logger.info(f"Creating secret '{secret_name}' (project: {project_id}, env: {env})")
        
        try:
            result = await self.client.secrets.create_secret_by_name(
                secret_name=secret_name,
                secret_value=secret_value,
                project_id=project_id,
                secret_path=path or self.secret_path,
                environment_slug=env,
                secret_comment=secret_comment,
                skip_multiline_encoding=skip_multiline_encoding,
                secret_reminder_repeat_days=secret_reminder_repeat_days,
                secret_reminder_note=secret_reminder_note,
            )
            
            # Invalidate cache for this project/env/path
            # Handle both empty path and default path cases
            paths_to_invalidate = [path or self.secret_path, ""]
            for path_to_check in paths_to_invalidate:
                cache_prefix = self._key(project_id, env, path_to_check)
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(cache_prefix)]
                for k in keys_to_remove:
                    del self._cache[k]
            
            logger.success(f"Successfully created secret: {secret_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create secret '{secret_name}': {e}")
            raise
    
    async def update_secret(
        self,
        current_secret_name: str,
        secret_value: Optional[str] = None,
        project: Optional[str] = None,
        env: Environment = "dev",
        path: Optional[str] = None,
        new_secret_name: Optional[str] = None,
        secret_comment: Optional[str] = None,
        skip_multiline_encoding: bool = False,
        secret_reminder_repeat_days: Optional[int] = None,
        secret_reminder_note: Optional[str] = None,
        secret_metadata: Optional[list] = None,
        tags_ids: Optional[list] = None,
    ) -> None:
        """
        Update an existing secret in Infisical.
        
        Args:
            current_secret_name: Current name of the secret
            secret_value: New value for the secret
            project: Project ID (uses default if not provided)
            env: Environment (dev, staging, prod)
            path: Secret path (uses default if not provided)
            new_secret_name: Optional new name for the secret
            secret_comment: Optional comment for the secret
            skip_multiline_encoding: Whether to skip multiline encoding
            secret_reminder_repeat_days: Days until reminder
            secret_reminder_note: Reminder note
            secret_metadata: Optional metadata for the secret
            tags_ids: Optional list of tag IDs
            
        Raises:
            Exception: If secret update fails
        """
        project_id = project or self.project_id
        if not project_id:
            raise ValueError("Project ID must be provided or set via INFISICAL_PROJECT_ID")
        
        logger.info(f"Updating secret '{current_secret_name}' (project: {project_id}, env: {env})")
        
        try:
            await self.client.secrets.update_secret_by_name(
                current_secret_name=current_secret_name,
                project_id=project_id,
                secret_path=path or self.secret_path,
                environment_slug=env,
                secret_value=secret_value,
                secret_comment=secret_comment,
                skip_multiline_encoding=skip_multiline_encoding,
                secret_reminder_repeat_days=secret_reminder_repeat_days,
                secret_reminder_note=secret_reminder_note,
                new_secret_name=new_secret_name,
                secret_metadata=secret_metadata or [],
                tags_ids=tags_ids or [],
            )
            
            # Invalidate cache for this project/env/path
            # Handle both empty path and default path cases
            paths_to_invalidate = [path or self.secret_path, ""]
            for path_to_check in paths_to_invalidate:
                cache_prefix = self._key(project_id, env, path_to_check)
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(cache_prefix)]
                for k in keys_to_remove:
                    del self._cache[k]
            
            logger.success(f"Successfully updated secret: {current_secret_name}")
            
        except Exception as e:
            logger.error(f"Failed to update secret '{current_secret_name}': {e}")
            raise
    
    async def secret_by_name(
        self,
        secret_name: str,
        project: Optional[str] = None,
        env: Environment = "dev",
        path: Optional[str] = None,
    ) -> BaseSecret:
        """
        Get a secret by name, returning the full BaseSecret object.
        
        Args:
            secret_name: Name of the secret
            project: Project ID (uses default if not provided)
            env: Environment (dev, staging, prod)
            path: Secret path (uses default if not provided)
            
        Returns:
            BaseSecret object containing full secret information
            
        Raises:
            Exception: If secret retrieval fails
        """
        project_id = project or self.project_id
        if not project_id:
            raise ValueError("Project ID must be provided or set via INFISICAL_PROJECT_ID")
        
        logger.info(f"Fetching secret object '{secret_name}' (project: {project_id}, env: {env})")
        
        try:
            secret = await self.client.secrets.get_secret_by_name(
                secret_name=secret_name,
                project_id=project_id,
                environment_slug=env,
                secret_path=path or self.secret_path,
            )
            
            logger.success(f"Successfully retrieved secret object: {secret_name}")
            return secret
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret object '{secret_name}': {e}")
            raise
