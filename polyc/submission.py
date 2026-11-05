"""Proposed v0alpha1 project intake: an immutable OCI *declaration*, not an executor.

Validation here proves schema consistency and signature integrity ONLY. It does not
fetch repositories, attest content, validate ethics, inspect Docker layers, or
establish that the image was built from the declared source.
"""
from __future__ import annotations
from pathlib import Path
from typing import Literal
import json
import re
import yaml
from pydantic import Field, model_validator
from .models import Strict
from .crypto import canonical, digest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

ID = r'^[a-z0-9][a-z0-9-]{2,63}$'
HEX64 = r'^[a-f0-9]{64}$'
IMAGE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9.:_-]*(?:/[a-zA-Z0-9._-]+)+@sha256:[a-f0-9]{64}$')


class Metadata(Strict):
    project_id: str = Field(pattern=ID)
    title: str = Field(min_length=4, max_length=120)
    revision: int = Field(ge=1)


class Source(Strict):
    repository: str = Field(pattern=r'^https://[A-Za-z0-9._/-]+$')
    commit: str = Field(pattern=r'^[a-f0-9]{40}$')
    license: str = Field(min_length=1, max_length=80)


class Artifact(Strict):
    image: str = Field(min_length=80, max_length=512)
    sbom_sha256: str | None = Field(default=None, pattern=HEX64)
    provenance_sha256: str | None = Field(default=None, pattern=HEX64)

    @model_validator(mode='after')
    def immutable(self):
        if not IMAGE.fullmatch(self.image):
            raise ValueError('OCI image must be pinned to a sha256 digest (registry/path@sha256:...)')
        return self


class Execution(Strict):
    adapter: Literal['polyc-task-json-v1'] = 'polyc-task-json-v1'
    task_count: int = Field(ge=1, le=100000)
    checkpointable: bool = True
    idempotent: bool = True
    network: Literal['none'] = 'none'
    root_filesystem_readonly: Literal[True] = True
    run_as_non_root: Literal[True] = True
    cpu_cores_max: float = Field(gt=0, le=128)
    memory_mib_max: int = Field(ge=128, le=1048576)
    gpu_count_max: int = Field(ge=0, le=16)
    wall_seconds_max: int = Field(ge=1, le=86400)
    output_mib_max: int = Field(ge=1, le=10240)
    verification: Literal['independent_recompute', 'project_verifier', 'human_review']


class ProjectManifest(Strict):
    apiVersion: Literal['polyc.home/v0alpha1']
    kind: Literal['ProjectManifest']
    metadata: Metadata
    source: Source
    artifact: Artifact
    execution: Execution


class Purpose(Strict):
    summary: str = Field(min_length=12, max_length=2000)
    category: str = Field(pattern=r'^[a-z][a-z0-9_]{0,63}$')
    declared_uses: list[str] = Field(min_length=1, max_length=16)
    prohibited_uses: list[str] = Field(default_factory=list, max_length=32)
    commercial: bool = False


class Participation(Strict):
    eligible_node_ids: list[str] = Field(default_factory=list, max_length=1000)
    excluded_node_ids: list[str] = Field(default_factory=list, max_length=1000)
    eligible_jurisdictions: list[str] = Field(default_factory=list, max_length=100)
    require_explicit_mutual_consent: Literal[True] = True
    owner_may_revoke: Literal[True] = True
    project_may_cancel: Literal[True] = True

    @model_validator(mode='after')
    def check_sets(self):
        if (set(self.eligible_node_ids) & set(self.excluded_node_ids)):
            raise ValueError('node cannot be simultaneously eligible and excluded')
        for a in [self.eligible_node_ids, self.excluded_node_ids, self.eligible_jurisdictions]:
            if len(a) != len(set(a)):
                raise ValueError('duplicate participation term')
        return self


class Distribution(Strict):
    mode: Literal['volunteer', 'credits', 'revenue_share']
    credit_per_verified_task: float = Field(ge=0, le=1000000)
    revenue_pool_percent: float = Field(ge=0, le=100, default=0)
    revenue_basis: Literal['gross_receipts', 'net_receipts'] | None = None
    preserve_earned_credits_on_cancellation: Literal[True] = True
    ledger_visibility: Literal['participants', 'public_pseudonymous'] = 'participants'
    payout_method: Literal['none', 'manual_external'] = 'none'
    output_license: str = Field(min_length=1, max_length=80)

    @model_validator(mode='after')
    def compensation_coherence(self):
        if self.mode != 'revenue_share' and self.revenue_basis is not None:
            raise ValueError('revenue basis only allowed with revenue_share mode')
        if self.mode != 'revenue_share' and self.revenue_pool_percent != 0:
            raise ValueError('revenue pool only allowed with revenue_share mode')
        if self.mode == 'revenue_share' and self.revenue_basis is None:
            raise ValueError('revenue_share must explicitly choose gross or net receipts')
        if self.mode == 'revenue_share' and self.revenue_pool_percent == 0:
            raise ValueError('revenue_share requires a positive pool percentage')
        if self.mode == 'volunteer' and self.credit_per_verified_task != 0:
            raise ValueError('volunteer mode may not silently accrue credits')
        return self


class RevenueStream(Strict):
    stream_id: str = Field(pattern=r'^[a-z][a-z0-9_-]{2,63}$')
    kind: Literal['patronage', 'sales', 'licensing', 'donations', 'grants', 'sponsorship', 'other']
    provider: str = Field(pattern=r'^[a-z][a-z0-9_-]{1,63}$')
    evidence: Literal['provider_statement', 'bank_statement', 'independent_audit', 'manual_declaration']
    included_in_revenue_share: bool = True


class FinancialDisclosure(Strict):
    """Unsigned provider activity is NOT proof of revenue. This is signed *intent only*."""
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    sources: list[RevenueStream] = Field(default_factory=list, max_length=32)
    receipts_definition: Literal['gross_receipts_less_tax_and_refunds',
                                 'net_after_declared_expenses']
    processor_fees_borne_by: Literal['project_owner', 'contributor_pool']
    settlement_cadence: Literal['monthly', 'quarterly', 'on_project_close']
    payout_rails: list[str] = Field(default_factory=list, max_length=16)
    minimum_payout_minor_units: int = Field(ge=0, le=1_000_000_000)
    dispute_window_days: int = Field(ge=7, le=365)
    contribution_terms_immutable: Literal[True] = True
    external_custody_only: Literal[True] = True
    real_payment_execution: Literal['not_implemented'] = 'not_implemented'

    @model_validator(mode='after')
    def unique_streams(self):
        if len(set(x.stream_id for x in self.sources)) != len(self.sources):
            raise ValueError('revenue stream ID duplicated')
        if len(set(self.payout_rails)) != len(self.payout_rails):
            raise ValueError('duplicate payout rail')
        if any(not re.fullmatch(r'[a-z][a-z0-9_-]{1,63}', v) for v in self.payout_rails):
            raise ValueError('invalid payout adapter name')
        return self


class ProjectTerms(Strict):
    purpose: Purpose
    participation: Participation
    distribution: Distribution
    financial_disclosure: FinancialDisclosure | None = None
    project_owner_pubkey: str = Field(pattern=HEX64)

    @model_validator(mode='after')
    def revenue_terms_need_disclosure(self):
        if self.distribution.mode == 'revenue_share' and self.financial_disclosure is None:
            raise ValueError('revenue-sharing projects must disclose financial streams and settlement terms')
        return self


class ProjectConstitution(Strict):
    apiVersion: Literal['polic.home/v0alpha1']
    kind: Literal['ProjectConstitution']
    metadata: Metadata
    spec: ProjectTerms


class Submission(Strict):
    manifest: ProjectManifest
    polic: ProjectConstitution

    @model_validator(mode='after')
    def compatible_revisions(self):
        if self.manifest.metadata != self.polic.metadata:
            raise ValueError('project ID/title/revision differ between project and PoliC constitution')
        if not self.manifest.source.repository.startswith('https://'):
            raise ValueError('project source must be public HTTPS')
        return self


class SignedSubmission(Strict):
    submission: Submission
    signer_pubkey: str = Field(pattern=HEX64)
    signature: str = Field(pattern=r'^[a-f0-9]{128}$')

    @model_validator(mode='after')
    def signer_corresponds_to_policy(self):
        if self.signer_pubkey != self.submission.polic.spec.project_owner_pubkey:
            raise ValueError('signer does not match owner key declared in PoliC constitution')
        return self


def load_submission(directory: str | Path) -> Submission:
    p = Path(directory)
    manifest = yaml.safe_load((p/'project.yaml').read_text(encoding='utf-8'))
    policy = yaml.safe_load((p/'polic.yaml').read_text(encoding='utf-8'))
    return Submission(manifest=ProjectManifest.model_validate(manifest),
                      polic=ProjectConstitution.model_validate(policy))


def submission_payload(s: Submission) -> dict:
    """Canonical v0.2-compatible shape: omit only NEW absent financial disclosure.

    Do not generally exclude None: v0.2 signed some null-valued existing fields.
    New signed financial disclosures remain inside the cryptographic commitment.
    """
    obj=s.model_dump(mode='json')
    if obj['polic']['spec'].get('financial_disclosure') is None:
        obj['polic']['spec'].pop('financial_disclosure', None)
    return obj


def submission_digest(s: Submission) -> str:
    return digest(submission_payload(s))


def sign_submission(s: Submission, private_file: str) -> SignedSubmission:
    private = serialization.load_pem_private_key(Path(private_file).read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise ValueError('expected Ed25519 key')
    pub = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    sig = private.sign(canonical(submission_payload(s))).hex()
    return SignedSubmission(submission=s, signer_pubkey=pub, signature=sig)


def verify_submission(signed: SignedSubmission) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(signed.signer_pubkey)).verify(
            bytes.fromhex(signed.signature), canonical(submission_payload(signed.submission)))
        return True
    except (InvalidSignature, ValueError):
        return False


def submission_compatibility(submission: Submission, node_constitution: dict,
                             node_id: str, verified_jurisdiction: str | None = None) -> list[str]:
    """Declared mutual compatibility preview. Does not attest identity, location, or source truth."""
    terms = submission.polic.spec
    node = node_constitution.get('spec', {})
    content = node.get('content', {})
    ethos = node.get('ethos', {})
    issues = []
    if terms.purpose.category not in content.get('allow_categories', []):
        issues.append('category not approved by node')
    if terms.purpose.category in content.get('deny_categories', []):
        issues.append('category prohibited by node')
    if set(terms.purpose.declared_uses) & set(ethos.get('exclude_projects_with_declared_purposes', [])):
        issues.append('declared purpose conflicts with node ethos')
    if terms.purpose.commercial and not ethos.get('allow_commercial_projects', False):
        issues.append('commercial usage not approved by node')
    if terms.participation.eligible_node_ids and node_id not in terms.participation.eligible_node_ids:
        issues.append('project does not consent to this contributor')
    if node_id in terms.participation.excluded_node_ids:
        issues.append('project explicitly excludes this contributor')
    if (terms.participation.eligible_jurisdictions and
            verified_jurisdiction not in terms.participation.eligible_jurisdictions):
        issues.append('project jurisdiction rule lacks matching verified jurisdiction')
    if terms.project_owner_pubkey not in node.get('trust', {}).get('trusted_signers', []):
        issues.append('project signer not trusted by node')
    if not all(content.get(k, False) for k in ['require_public_repository',
                                               'require_pinned_source_commit', 'require_signed_artifacts']):
        issues.append('node lacks required public-source/signed declaration guardrails')
    if node.get('sovereignty', {}).get('require_mutual_consent') is not True:
        issues.append('node mutual consent invariant disabled')
    return issues
