"""Immutable artifact storage."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .errors import PersistenceError


class ArtifactChecksumMismatch(PersistenceError):
    def __init__(self, key: str) -> None:
        super().__init__(
            "artifact_checksum_mismatch",
            f"checksum mismatch for artifact key {key}",
        )


class ArtifactExists(PersistenceError):
    def __init__(self, key: str) -> None:
        super().__init__(
            "artifact_exists",
            f"artifact key already exists: {key}",
        )


class ArtifactWriteError(PersistenceError):
    def __init__(self, key: str, reason: str) -> None:
        super().__init__(
            "artifact_write_failed",
            f"failed to write artifact {key}: {reason}",
        )


@dataclass(frozen=True)
class StoredArtifact:
    key: str
    checksum_sha256: str
    size_bytes: int


class ArtifactStore(Protocol):
    def write_immutable(
        self, key: str, data: bytes, *, expected_checksum: str | None = None
    ) -> StoredArtifact: ...

    def read(self, key: str) -> bytes: ...

    def checksum(self, key: str) -> str: ...

    def exists(self, key: str) -> bool: ...

    def list_keys(self) -> list[str]: ...


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FilesystemArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if ".." in key.split("/") or key.startswith("/"):
            raise PersistenceError("invalid_artifact_key", f"invalid key: {key}")
        return self._root / key

    def write_immutable(
        self, key: str, data: bytes, *, expected_checksum: str | None = None
    ) -> StoredArtifact:
        digest = sha256_hex(data)
        if expected_checksum is not None and digest != expected_checksum:
            raise ArtifactChecksumMismatch(key)
        path = self._path(key)
        if path.exists():
            existing = path.read_bytes()
            if sha256_hex(existing) != digest:
                raise ArtifactChecksumMismatch(key)
            return StoredArtifact(key=key, checksum_sha256=digest, size_bytes=len(data))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except OSError as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise ArtifactWriteError(key, str(exc)) from exc
        return StoredArtifact(key=key, checksum_sha256=digest, size_bytes=len(data))

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def checksum(self, key: str) -> str:
        return sha256_hex(self.read(key))

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def list_keys(self) -> list[str]:
        keys: list[str] = []
        for path in self._root.rglob("*"):
            if path.is_file() and not path.name.endswith(".tmp"):
                keys.append(path.relative_to(self._root).as_posix())
        return sorted(keys)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3ArtifactStore:
    """Production adapter; requires ARTIFACT_* configuration (Run 19)."""

    @staticmethod
    def from_env() -> ArtifactStore:
        endpoint = os.environ.get("ARTIFACT_ENDPOINT", "").strip()
        bucket = os.environ.get("ARTIFACT_BUCKET", "").strip()
        if not endpoint or not bucket:
            raise PersistenceError(
                "artifact_store_unconfigured",
                "S3-compatible artifact storage is not configured; "
                "set ARTIFACT_ENDPOINT and ARTIFACT_BUCKET or use FilesystemArtifactStore",
            )
        raise NotImplementedError(
            "S3 artifact adapter is not implemented in Run 03; configure filesystem locally"
        )
