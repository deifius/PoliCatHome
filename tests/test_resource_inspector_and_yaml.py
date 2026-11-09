"""The inspector must be voluntary and exported YAML must round-trip exactly."""
from html.parser import HTMLParser
from pathlib import Path
import json
import subprocess
import yaml
from polyc.demo import constitution

ROOT=Path(__file__).resolve().parents[1]

class IDs(HTMLParser):
    def __init__(self):
        super().__init__();self.ids={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids[attrs['id']]=(tag,attrs)

def test_inspection_does_not_affect_consent():
    html=(ROOT/'polyc/web/index.html').read_text()
    ui=IDs();ui.feed(html)
    for identifier in ('inspectResourcesBtn','resourceResults','resourceStatus','gpuProofBtn',
                       'resourceCpu','resourceRam','resourceGpu','resourceGl','resourceSensors',
                       'previewPolicBtn','exportYamlBtn','exportPolicBtn','policPreview'):
        assert identifier in ui.ids
    assert 'hidden' in ui.ids['resourceResults'][1]
    assert 'hidden' in ui.ids['policPreview'][1]
    assert 'checked' not in ui.ids['browserConsent'][1]
    assert 'No inspection has run yet' in html
    assert 'separate opt-in diagnostic' in html
    js=(ROOT/'polyc/web/app.js').read_text()
    assert 'inspectResources' in js and 'proveWebGpu' in js
    assert "$('inspectResourcesBtn').onclick=inspectMyBrowser" in js
    assert "$('gpuProofBtn').onclick=gpuProof" in js
    assert "const constitution=registered?state.node.constitution:await draftPolic();" in js
    assert "state.node.constitution" in js
    assert 'No device readings or authentication tokens are included' in js


def test_yaml_round_trip():
    sample=constitution('0'*64)
    sample['spec']['trust']['trusted_signers']=[]
    sample['spec']['thermal']['cpu_package_c_max']=None
    script="""import {asPolicYaml} from './polyc/web/polic-yaml.js';
import fs from 'node:fs';console.log(asPolicYaml(JSON.parse(fs.readFileSync(0,'utf8'))));"""
    result=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps(sample),text=True,cwd=ROOT,capture_output=True,check=True)
    assert yaml.safe_load(result.stdout)==sample
    assert 'token:' not in result.stdout


def test_resource_probe_optional_and_no_network():
    js=(ROOT/'polyc/web/resource-inspector.js').read_text()
    assert 'fetch(' not in js
    assert 'sendBeacon(' not in js
    assert 'temperature:null' in js
    assert 'fanRPM:null' in js
    assert 'totalVramGiB:null' in js
    assert 'device.queue.submit' in js
