#!/usr/bin/env python3
"""Offline render and cross-resource checks; does not access a cluster."""
import json
import subprocess
from pathlib import Path

import yaml


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys that ordinary YAML parsing silently overwrites."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def parse(text):
    return [doc for doc in yaml.load_all(text, Loader=UniqueLoader) if doc is not None]


def run(*args):
    return subprocess.check_output(args, text=True)


def pod_spec(doc):
    if doc.get('kind') == 'Pod':
        return doc['spec']
    if doc.get('kind') in ('Deployment', 'StatefulSet', 'Job'):
        return doc['spec']['template']['spec']
    if doc.get('kind') == 'CronJob':
        return doc['spec']['jobTemplate']['spec']['template']['spec']
    return None


def check_resources(docs):
    identities = set()
    for doc in docs:
        identity = (doc['kind'], doc['metadata'].get('namespace'), doc['metadata']['name'])
        assert identity not in identities, f'Duplicate resource: {identity}'
        identities.add(identity)
        spec = pod_spec(doc)
        if spec:
            volumes = [v['name'] for v in spec.get('volumes', [])]
            volumes += [v['metadata']['name'] for v in doc.get('spec', {}).get('volumeClaimTemplates', [])]
            assert len(volumes) == len(set(volumes)), f'Duplicate volume in {identity}'
            for container in spec['containers']:
                mounts = container.get('volumeMounts', [])
                assert len({m['mountPath'] for m in mounts}) == len(mounts), identity
                assert all(m['name'] in volumes for m in mounts), identity
        if doc['kind'] in ('Deployment', 'StatefulSet'):
            labels = doc['spec']['template']['metadata']['labels']
            selector = doc['spec']['selector']['matchLabels']
            assert all(labels.get(k) == v for k, v in selector.items()), identity
    for service in (d for d in docs if d['kind'] == 'Service'):
        namespace = service['metadata'].get('namespace')
        selector = service['spec']['selector']
        targets = [d for d in docs if d['kind'] in ('Deployment', 'StatefulSet')
                   and d['metadata'].get('namespace') == namespace
                   and all(d['spec']['template']['metadata']['labels'].get(k) == v
                           for k, v in selector.items())]
        assert targets, f'No workload for Service {service["metadata"]["name"]}'
        for target in targets:
            ports = {p['containerPort'] for c in pod_spec(target)['containers'] for p in c.get('ports', [])}
            assert all(p.get('targetPort', p['port']) in ports for p in service['spec']['ports']), service


root = Path(__file__).resolve().parents[1]
assert Path.cwd() == root, 'Run through scripts/validate-kubernetes.sh from the repository.'
files = sorted(Path('kubernetes').rglob('*.yaml')) + sorted(Path('overlays').rglob('*.yaml'))
for path in files:
    for doc in parse(path.read_text()):
        if doc.get('kind') == 'ConfigMap':
            for key, content in doc.get('data', {}).items():
                if key.endswith(('.yaml', '.yml')):
                    parse(content)
                elif key.endswith('.json'):
                    json.loads(content)
print(f'Parsed {len(files)} YAML files and embedded YAML/JSON configurations.')

print(run('helm', 'lint', 'helm/taskflow').strip())
base = parse(run('kubectl', 'kustomize', 'kubernetes'))
production = parse(run('kubectl', 'kustomize', 'overlays/10-production'))
helm = parse(run('helm', 'template', 'taskflow', 'helm/taskflow', '--namespace', 'taskflow-helm'))
custom = parse(run('helm', 'template', 'taskflow', 'helm/taskflow', '--namespace', 'custom-lab',
                   '--set', 'api.replicas=4', '--set', 'frontend.replicas=1',
                   '--set-string', 'api.image=example/api:test', '--set-string', 'existingSecret=custom-secret'))
for name, docs in [('base', base), ('production', production), ('Helm defaults', helm), ('Helm overrides', custom)]:
    check_resources(docs)
    print(f'{name}: {len(docs)} resources; selectors, Service ports and volume mounts verified.')

for doc in custom:
    assert doc['metadata']['namespace'] == 'custom-lab'
api = next(d for d in custom if d['kind'] == 'Deployment' and d['metadata']['name'] == 'taskflow-api')
assert api['spec']['replicas'] == 4
assert pod_spec(api)['containers'][0]['image'] == 'example/api:test'
assert pod_spec(api)['containers'][0]['envFrom'][1]['secretRef']['name'] == 'custom-secret'
assert not any(d['kind'] == 'Secret' for d in helm + production)
assert not any(d['kind'] == 'RoleBinding' and d['metadata']['name'] == 'taskflow-readonly' for d in production)
for doc in production:
    spec = pod_spec(doc)
    if not spec:
        continue
    assert spec['automountServiceAccountToken'] is False
    assert spec['securityContext']['runAsNonRoot'] is True
    assert spec['securityContext']['runAsUser'] > 0
    assert spec['securityContext']['seccompProfile']['type'] == 'RuntimeDefault'
    for container in spec['containers']:
        security = container['securityContext']
        assert security['allowPrivilegeEscalation'] is False
        assert security['capabilities']['drop'] == ['ALL']
        if doc['metadata']['name'] != 'postgres':
            assert security['readOnlyRootFilesystem'] is True

sql = Path('database/init.sql').read_text()
for docs in (base, helm):
    init = next(d for d in docs if d['kind'] == 'ConfigMap' and d['metadata']['name'] == 'postgres-init')
    assert init['data']['init.sql'] == sql, 'Database initialization SQL is out of sync.'

observability = []
for folder in ('kubernetes/08-monitoring', 'kubernetes/09-logging'):
    for path in sorted(Path(folder).glob('*.yaml')):
        observability.extend(parse(path.read_text()))
check_resources(observability)
print('Verified external Secret ownership, non-root hardening, Helm overrides and SQL parity.')
print('Static checks passed. Live rollout, CNI enforcement, image startup and restore checks still require a cluster.')
