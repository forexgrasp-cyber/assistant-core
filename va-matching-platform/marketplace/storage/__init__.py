"""
Document storage — thin adapter over the canonical cloud storage service.

Provider selection, upload/download, tier limits, and migration logic are
canonical (``shared.cloud_storage.CloudStorageService`` — Oracle ObjSt,
Cloudflare R2, GCS/Firebase, AWS S3, Azure Blob). This module only maps
marketplace documents (VA vetting artifacts, trial tasks, deliverables)
onto that service.

Env (canonical): AWS_* / ORACLE_* / R2_* / GCS_* / AZURE_* keys.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any
from uuid import uuid4

import structlog

from shared.cloud_storage.service import CloudStorageService

__all__ = ["DocumentStorage", "get_document_storage", "DocKind"]

log = structlog.get_logger(__name__)

DocKind = str  # vetting_test | trial_task | deliverable | resume


class DocumentStorage:
    """Marketplace document storage on the canonical multi-provider backend.

    Canonical primitives reused:
        CloudStorageService.upload_video      file → Oracle/R2/GCS/S3/Azure
        CloudStorageService.get_video_stream_url signed/streaming read URL
        CloudStorageService.delete_artifact   provider-side delete
        CloudStorageService.get_storage_stats quota/usage reporting
    """

    def __init__(self):
        self._cloud = CloudStorageService()

    @property
    def backend(self) -> CloudStorageService:
        return self._cloud

    def _object_name(self, owner_id: str, kind: DocKind, filename: str) -> str:
        ext = ""
        if "." in filename:
            ext = filename.rsplit(".", 1)[-1][:10]
        name = f"va/{kind}/{owner_id}/{uuid4().hex}"
        if ext:
            name += f".{ext}"
        return name

    async def store_document(
        self,
        *,
        owner_id: str,
        kind: DocKind,
        content: bytes,
        filename: str = "document.bin",
        content_type: str = "application/octet-stream",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Spool the document and upload via the canonical provider."""
        tmp_dir = tempfile.mkdtemp(prefix="va_doc_")
        path = os.path.join(tmp_dir, os.path.basename(filename) or "document.bin")
        try:
            with open(path, "wb") as fh:
                fh.write(content)
            result = self._cloud.upload_video(
                video_path=path,
                schedule_id=kind,
                metadata={
                    "kind": kind,
                    "owner_id": owner_id,
                    "filename": filename,
                    "content_type": content_type,
                    **(metadata or {}),
                },
                user_id=owner_id,
            )
        finally:
            try:
                os.remove(path)
                os.rmdir(tmp_dir)
            except OSError:
                pass
        log.info("document_stored", kind=kind, owner_id=owner_id,
                 video_id=result.get("video_id"))
        return {"document_id": result.get("video_id"), "result": result}

    def retrieve_document(self, document_id: str, provider: str = "auto") -> str:
        """Signed/streaming URL for a stored document (canonical provider)."""
        return self._cloud.get_video_stream_url(document_id, provider=provider)

    async def delete_document(self, document_id: str) -> dict[str, Any]:
        return self._cloud.delete_artifact(document_id, artifact_type="video")

    def storage_stats(self) -> dict[str, Any]:
        """Canonical usage/quota reporting."""
        return self._cloud.get_storage_stats()

    def available_backends(self) -> dict[str, bool]:
        """Which canonical providers are configured right now."""
        return {
            "oracle": bool(self._cloud.oracle_available),
            "cloudflare_r2": bool(self._cloud.cloudflare_available),
            "gcs_firebase": bool(self._cloud.gcs_available),
            "aws_s3": bool(self._cloud.aws_s3_available),
            "azure_blob": bool(self._cloud.azure_blob_available),
        }


_document_storage: DocumentStorage | None = None


def get_document_storage() -> DocumentStorage:
    """Cached document storage adapter."""
    global _document_storage
    if _document_storage is None:
        _document_storage = DocumentStorage()
    return _document_storage
