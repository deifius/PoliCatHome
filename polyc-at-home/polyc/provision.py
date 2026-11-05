"""Offline setup for a real five-host pilot; keep credentials out of Git."""
from __future__ import annotations
import json
import secrets
from pathlib import Path
import yaml
from .crypto import create_keypair, sign_project
from .demo import constitution
from .models import Project


def provision(root_path: str, nodes: int = 5) -> Path:
    if not 1 <= nodes <= 25:
        raise ValueError('node count must be 1..25')
    root = Path(root_path)
    root.mkdir(parents=True, exist_ok=False)
    (root/'nodes').mkdir()
    create_keypair(str(root/'project.pem'),str(root/'project.pub'))
    pub = (root/'project.pub').read_text()
    admin = secrets.token_urlsafe(32)
    (root/'admin-token.txt').write_text(admin+'\n')
    (root/'admin-token.txt').chmod(0o600)
    for i in range(1,nodes+1):
        node_id=f'cat-{i}'
        node_const=constitution(pub)
        node_const['metadata']['name']=node_id
        cfg={'node_id':node_id,'token':secrets.token_urlsafe(32),'constitution':node_const,
             'pause_file':f'runtime/{node_id}.pause'}
        target=root/'nodes'/f'{node_id}.yaml'
        target.write_text(yaml.safe_dump(cfg,sort_keys=False))
        target.chmod(0o600)
    project=Project(project_id='five-cats-open-science',title='Five Cats Compute Together',
                    source_repo='https://github.com/example/public-open-science',source_commit='a'*40,
                    category='open_science',purposes=['open_knowledge'],commercial=False,
                    work={'tasks':25,'iterations':5000,'seed':'catnap'})
    (root/'project.yaml').write_text(yaml.safe_dump(project.model_dump(mode='json'),sort_keys=False))
    signed=sign_project(project,str(root/'project.pem'))
    (root/'signed-project.json').write_text(signed.model_dump_json(indent=2)+'\n')
    (root/'README.txt').write_text('PRIVATE pilot credentials; do not commit this directory.\n'
         'Admin token grants node enrollment and project submission. Send each owner ONLY their node YAML.\n'
         'Replace the placeholder repository and source hash before use beyond the built-in demonstration.\n')
    return root
