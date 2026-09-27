"""Pipeline stage manifest for replay and diagnostics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StageManifestEntry:
    stage: str
    producer_version: str
    input_hash: str
    artifact_uri: str | None
    status: str
    warnings: list[str]

    def to_wire(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "producerVersion": self.producer_version,
            "inputHash": self.input_hash,
            "artifactUri": self.artifact_uri,
            "status": self.status,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class PipelineManifest:
    schema_version: str = "1.0"
    pipeline_version: str = ""
    profile_version: str = ""
    stages: tuple[StageManifestEntry, ...] = ()

    def to_bytes(self) -> bytes:
        payload = {
            "schemaVersion": self.schema_version,
            "pipelineVersion": self.pipeline_version,
            "profileVersion": self.profile_version,
            "stages": [entry.to_wire() for entry in self.stages],
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
