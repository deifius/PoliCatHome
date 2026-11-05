import copy
import pytest
from polyc.crypto import verify_project
from polyc.policy import compatible, validate_constitution, ConstitutionError


def test_signature_tampering_and_untrusted_signer(setup):
    _, _, _, sign, pub = setup
    sp = sign()
    assert verify_project(sp, [pub])
    assert not verify_project(sp, ['0'*64])
    changed = sp.model_copy(deep=True)
    changed.project.title = 'Fraudulent arithmetic'
    assert not verify_project(changed,[pub])


def test_constitution_invariants(setup):
    _, _, c, _, _ = setup
    broken = copy.deepcopy(c)
    broken['spec']['sovereignty']['owner_can_revoke_immediately'] = False
    with pytest.raises(ConstitutionError):
        validate_constitution(broken)
    broken = copy.deepcopy(c)
    broken['spec']['nice_plus']['memory_mib_max']=128
    with pytest.raises(ConstitutionError):
        validate_constitution(broken)
    broken = copy.deepcopy(c)
    broken['spec']['energy']['require_meter']=True
    with pytest.raises(ConstitutionError):
        validate_constitution(broken)


def test_bidirectional_constitutional_matching(setup):
    _, _, c, sign, _ = setup
    assert not compatible(c, sign().project, 'cat-one')
    assert 'category not explicitly allowed' in compatible(c, sign(category='weapons').project, 'cat-one')
    assert 'declared purpose conflicts with node ethos' in compatible(c, sign(purposes=['ethnic_cleansing']).project, 'cat-one')
    assert 'commercial project not permitted' in compatible(c, sign(commercial=True).project, 'cat-one')
    assert 'project has not consented to this contributor' in compatible(c, sign(contributor_allowlist=['cat-two']).project, 'cat-one')
    assert 'project rejects this contributor' in compatible(c, sign(contributor_denylist=['cat-one']).project, 'cat-one')
