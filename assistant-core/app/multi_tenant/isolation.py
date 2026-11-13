"""Tenant isolation - database and resource isolation per tenant."""

from __future__ import annotations

from pathlib import Path


class TenantIsolation:
    """Manages tenant isolation for data and resources."""

    def __init__(self, base_data_dir: str):
        self.base_data_dir = Path(base_data_dir)
        self.base_data_dir.mkdir(parents=True, exist_ok=True)

    def get_tenant_dir(self, tenant_id: str) -> Path:
        """Get tenant-specific data directory."""
        tenant_dir = self.base_data_dir / "tenants" / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir

    def get_assistant_dir(self, tenant_id: str, assistant_id: str) -> Path:
        """Get assistant-specific data directory."""
        assistant_dir = self.get_tenant_dir(tenant_id) / "assistants" / assistant_id
        assistant_dir.mkdir(parents=True, exist_ok=True)
        return assistant_dir

    def get_database_url(self, tenant_id: str, assistant_id: str | None = None) -> str:
        """Get SQLite database URL for tenant/assistant."""
        if assistant_id:
            db_path = self.get_assistant_dir(tenant_id, assistant_id) / "assistant.db"
        else:
            db_path = self.get_tenant_dir(tenant_id) / "tenant.db"
        return f"sqlite:///{db_path}"

    def get_chromadb_path(self, tenant_id: str, assistant_id: str | None = None) -> str:
        """Get ChromaDB path for tenant/assistant."""
        if assistant_id:
            return str(self.get_assistant_dir(tenant_id, assistant_id) / "chromadb")
        return str(self.get_tenant_dir(tenant_id) / "chromadb")

    def isolate_database(self, tenant_id: str) -> str:
        """Get isolated database URL for tenant."""
        return self.get_database_url(tenant_id)

    def cleanup_tenant(self, tenant_id: str) -> bool:
        """Remove all tenant data (use with caution)."""
        import shutil
        tenant_dir = self.get_tenant_dir(tenant_id)
        if tenant_dir.exists():
            shutil.rmtree(tenant_dir)
            return True
        return False