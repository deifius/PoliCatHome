"""PoliC: deterministic declared-policy compatibility, not ideological inference."""
from __future__ import annotations
from .models import Project
from .crypto import digest

class ConstitutionError(ValueError):
    pass


def validate_constitution(c: dict) -> None:
    if c.get('apiVersion') != 'polic.home/v0alpha1' or c.get('kind') != 'NodeConstitution':
        raise ConstitutionError('unsupported constitution kind/version')
    s = c.get('spec', {})
    sv = s.get('sovereignty', {})
    if not all(sv.get(x) is True for x in ['local_workloads_first', 'owner_can_revoke_immediately', 'require_mutual_consent']):
        raise ConstitutionError('sovereignty invariants are mandatory')
    nice = s.get('nice_plus', {})
    if not (20 <= nice.get('level', 0) <= 99):
        raise ConstitutionError('nice_plus level must be 20..99 (application policy)')
    if not (1 <= nice.get('cpu_percent_max', 0) <= 100):
        raise ConstitutionError('cpu limit missing or invalid')
    if not (512 <= nice.get('memory_mib_max', 0) <= 8192):
        raise ConstitutionError('memory MiB must be 512..8192 for the pilot Python runtime')
    if not (1 <= nice.get('task_runtime_seconds_max', 0) <= 300):
        raise ConstitutionError('task runtime must be 1..300 seconds')
    if not isinstance(s.get('content', {}).get('allow_categories'), list):
        raise ConstitutionError('content allow_categories required')
    if s.get('thermal', {}).get('missing_sensor_action') not in ('deny', 'pause'):
        raise ConstitutionError('thermal missing sensor action required')
    if s.get('thermal', {}).get('cpu_package_c_max') is not None and not (35 <= s['thermal']['cpu_package_c_max'] <= 105):
        raise ConstitutionError('invalid CPU temperature threshold')
    if not isinstance(s.get('trust', {}).get('trusted_signers'), list):
        raise ConstitutionError('trusted signers required')
    if s.get('energy', {}).get('require_meter', False):
        raise ConstitutionError('energy meter enforcement not implemented in pilot; deny by default')
    if s.get('nice_plus', {}).get('gpu_utilization_percent_max', 0):
        raise ConstitutionError('GPU workload enforcement not implemented in pilot')
    financial = s.get('financial')
    if financial is not None:
        if not isinstance(financial, dict) or financial.get('test_credits_enabled') is not True:
            raise ConstitutionError('only explicit test-credit financial opt-in supported')
        pub = financial.get('wallet_pubkey', '')
        if not (isinstance(pub, str) and len(pub) == 64 and all(ch in '0123456789abcdef' for ch in pub)):
            raise ConstitutionError('node financial wallet Ed25519 public key required')
        assets = financial.get('accepted_assets')
        if not isinstance(assets,list) or not assets or any(not isinstance(a,str) for a in assets):
            raise ConstitutionError('accepted credit assets must be declared')
        if not (1 <= financial.get('minimum_credits_per_task',0) <= 10000):
            raise ConstitutionError('minimum credit compensation must be 1..10000')


def compatible(constitution: dict, project: Project, node_id: str) -> list[str]:
    """Return human-readable rejection reasons. Empty means declared-policy match."""
    s = constitution['spec']; content = s.get('content', {}); ethos = s.get('ethos', {})
    issues: list[str] = []
    if project.category not in content.get('allow_categories', []):
        issues.append('category not explicitly allowed')
    if project.category in content.get('deny_categories', []):
        issues.append('category denied')
    if set(project.purposes) & set(ethos.get('exclude_projects_with_declared_purposes', [])):
        issues.append('declared purpose conflicts with node ethos')
    if project.commercial and not ethos.get('allow_commercial_projects', False):
        issues.append('commercial project not permitted')
    if project.contributor_allowlist and node_id not in project.contributor_allowlist:
        issues.append('project has not consented to this contributor')
    if node_id in project.contributor_denylist:
        issues.append('project rejects this contributor')
    if not content.get('require_public_repository', False):
        issues.append('pilot requires public repository policy')
    if not content.get('require_pinned_source_commit', False):
        issues.append('pilot requires pinned source commit policy')
    if not content.get('require_signed_artifacts', False):
        issues.append('pilot requires signed project declarations')
    if not project.source_repo.startswith('https://') or len(project.source_commit) != 40:
        issues.append('missing public repository or pinned commit')
    if project.work.kind != 'sha256_chain_v1':
        issues.append('work type is not built in')
    financial=project.financial
    if financial and financial.model == 'test_credits':
        options=s.get('financial',{})
        if (options.get('test_credits_enabled') is not True or
            financial.asset_id not in options.get('accepted_assets',[]) or
            not options.get('wallet_pubkey')):
            issues.append('node did not opt in to test-credit payment and wallet settlement')
        if financial.credits_per_verified_task < options.get('minimum_credits_per_task', 1):
            issues.append('task credit compensation below node constitutional minimum')
    return issues


def policy_digest(c: dict) -> str:
    return digest(c)
