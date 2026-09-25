"""Read-only evidence capture and Step QA of an existing real branch video."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('session')
parser.add_argument('branch')
parser.add_argument('label')
parser.add_argument('--expected', default='')
args = parser.parse_args()
assert re.fullmatch('[a-z0-9_]+', args.label)
base = 'http://127.0.0.1:9000'
state = json.load(urlopen(base + '/api/dev/sessions/' + args.session + '/state'))
branch = next(b for b in state['branches'] if b['id'] == args.branch)
folder = ROOT / 'docs/acceptance/biohazard_full_e2e/visual_qa'
output = folder / (args.label + '_step5.json')
assert not output.exists(), 'Preserve earlier QA; do not repeat a paid text review accidentally'
video = folder / (args.label + '.mp4')
url = base + '/media/' + branch['artifact']['assembled_path']
if not video.exists():
    video.write_bytes(urlopen(url).read())
refs = {}
for shot in branch['shots']:
    for ref in shot['references']:
        if ref['role'] in ('front', 'wardrobe'):
            refs[ref['asset_id']] = {'id': ref['asset_id'], 'role': ref['role'], 'url': ref['path'], 'character': ref['entity']}
assets = folder / (args.label + '_references.json')
assets.write_text(json.dumps(list(refs.values()), ensure_ascii=False, indent=2))
context = folder / (args.label + '_context.json')
context.write_text(json.dumps({'session_id': args.session, 'branch_id': args.branch,
    'narrative': branch['narrative'], 'shot_prompts': [s['prompt'] for s in branch['shots']],
    'expected_characters': [s['params']['cast'] for s in branch['shots']],
    'expected_action': args.expected or branch['label'],
    'jobs': branch['jobs'], 'artifact': branch['artifact']}, ensure_ascii=False, indent=2))
subprocess.run([str(ROOT / 'backend/.venv/bin/python'), str(ROOT / 'tools/visual_qa.py'),
    '--mode', 'video', '--assets', str(assets), '--video', str(video),
    '--context', str(context), '--output', str(output)], check=True, cwd=ROOT)
