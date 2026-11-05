"""Strict public protocol structures. There is no arbitrary command field."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkSpec(Strict):
    kind: Literal["sha256_chain_v1"] = "sha256_chain_v1"
    tasks: int = Field(ge=1, le=100)
    iterations: int = Field(ge=1, le=400000)
    seed: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")


class ProjectFinancial(Strict):
    model: Literal["volunteer", "test_credits"] = "volunteer"
    asset_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9._-]{3,79}$")
    credits_per_verified_task: int = Field(default=0, ge=0, le=10000)

    @model_validator(mode="after")
    def validate_funding(self):
        if self.model == "volunteer" and (self.asset_id is not None or self.credits_per_verified_task):
            raise ValueError("volunteer work has no promised credit payments")
        if self.model == "test_credits" and (not self.asset_id or not self.credits_per_verified_task):
            raise ValueError("credit-funded work must specify asset and cost per verified task")
        return self


class Project(Strict):
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    title: str = Field(min_length=4, max_length=120)
    source_repo: str = Field(pattern=r"^https://[A-Za-z0-9._/-]+$")
    source_commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    category: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    purposes: list[str] = Field(min_length=1, max_length=16)
    commercial: bool = False
    contributor_allowlist: list[str] = Field(default_factory=list)
    contributor_denylist: list[str] = Field(default_factory=list)
    financial: ProjectFinancial | None = None
    work: WorkSpec

    @field_validator('purposes', 'contributor_allowlist', 'contributor_denylist')
    @classmethod
    def safe_items(cls, items: list[str]) -> list[str]:
        if len(items) > 100 or len(items) != len(set(items)):
            raise ValueError('too many or duplicate items')
        if not all(1 <= len(s) <= 80 and s.replace('_', '').replace('-', '').isalnum() for s in items):
            raise ValueError('invalid values')
        return items


class SignedProject(Strict):
    project: Project
    signer_pubkey: str = Field(min_length=64, max_length=64)
    signature: str = Field(min_length=128, max_length=128)


class NodeRegistration(Strict):
    node_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    token: str = Field(min_length=24, max_length=256)
    constitution: dict


class LeaseRequest(Strict):
    node_id: str
    constitution_digest: str


class TaskComplete(Strict):
    node_id: str
    lease_id: str
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    duration_seconds: float = Field(ge=0, le=3600)


class TaskFail(Strict):
    node_id: str
    lease_id: str
    reason: str = Field(min_length=1, max_length=200)
