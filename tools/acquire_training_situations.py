"""Bounded official BST acquisition; private source-disjoint editorial queue.

No dialogue becomes an SFT target here. Never opens the sealed final texts.
CC BY data and original MIT code have separate provenance. No archive extract.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import tarfile

from dialogue_eval_core import digest, normalized, pii_risk, private_root, save
from prepare_dialogue_evaluation import PARLAI, fetch

ARCHIVE_SHA = '5fbed0068ee89e2d43b93c3ecb341e784617033efa5e8e911a219d4eda6134a6'
LICENSE_URL = f'https://raw.githubusercontent.com/facebookresearch/ParlAI/{PARLAI}/parlai/tasks/blended_skill_talk/LICENSE_DOCUMENTATION'
ARCHIVE_URL = 'https://parl.ai/downloads/blended_skill_talk/blended_skill_talk.tar.gz'
ATTRIBUTION = 'Eric Michael Smith et al., Blended Skill Talk, ACL 2020; Meta/Facebook ParlAI'


def episodes(raw):
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA:
        raise ValueError('Official archive checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = [m for m in archive.getmembers() if m.name.split('/')[-1] == 'train.json']
        if len(members) != 1 or not members[0].isfile() or members[0].size > 20 * 1024**2:
            raise ValueError('Exactly one bounded regular train JSON required')
        with archive.extractfile(members[0]) as stream:
            return json.load(stream)


def family(ep):
    return digest(dict(personas=ep.get('personas'), seed=[ep.get('free_turker_utterance'), ep.get('guided_turker_utterance')]))


def seeds(ep):
    return {normalized(ep.get(k, '')) for k in ('free_turker_utterance', 'guided_turker_utterance')} - {''}


def select(rows, old_indices):
    """Reserve complete seed families, not just rows that happened to be evaluated."""
    if any(type(i) is not int or not 0 <= i < len(rows) for i in old_indices):
        raise ValueError('Unknown prior source index')
    blocked_groups = {family(rows[i]) for i in old_indices}
    blocked_seeds = set().union(*(seeds(rows[i]) for i in old_indices)) if old_indices else set()
    # Transitive shared-seed closure: a different partner cannot launder a seed.
    changed = True
    while changed:
        changed = False
        for ep in rows:
            if family(ep) in blocked_groups or seeds(ep) & blocked_seeds:
                before = len(blocked_groups), len(blocked_seeds)
                blocked_groups.add(family(ep)); blocked_seeds.update(seeds(ep))
                changed |= before != (len(blocked_groups), len(blocked_seeds))
    candidates, excluded, seen = [], Counter(), set()
    for i, ep in enumerate(rows):
        if ep.get('context_dataset') not in ('convai2', 'wizard_of_wikipedia'):
            excluded['NC_related_ED_seed'] += 1; continue
        group = family(ep)
        if group in blocked_groups:
            excluded['prior_evaluation_or_shared_seed'] += 1; continue
        dialogue = ep.get('dialog', [])
        text = [ep.get('free_turker_utterance', ''), ep.get('guided_turker_utterance', '')]
        text += [turn[1] for turn in dialogue if isinstance(turn, list) and len(turn) == 2]
        if len(text) < 4 or any(not isinstance(t, str) or not 1 <= len(t) <= 1500 or pii_risk(t) for t in text):
            excluded['privacy_or_length'] += 1; continue
        signature = digest([normalized(t) for t in text])
        if signature in seen:
            excluded['exact_dialogue_duplicate'] += 1; continue
        seen.add(signature)
        candidates.append(dict(source_index=i, group='bst:' + group, source_family=ep['context_dataset'],
            seed_keys=sorted(digest(s) for s in seeds(ep)), dialogue_sha256=signature, text=text,
            license='CC-BY-4.0', attribution=ATTRIBUTION, status='UNREVIEWED_NOT_TRAINING'))
    # Connected components over remaining seeds also stay in one split.
    parent = list(range(len(candidates)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    keys = {}
    for i, row in enumerate(candidates):
        for key in [row['group'], *row['seed_keys']]:
            if key in keys: parent[find(i)] = find(keys[key])
            else: keys[key] = i
    components = {}
    for i, row in enumerate(candidates): components.setdefault(find(i), []).append(row)
    for members in components.values():
        identity = digest(sorted(r['group'] for r in members)); bucket = int(identity[:8], 16) % 10
        split = 'development' if bucket == 8 else 'independent' if bucket == 9 else 'train'
        for row in members: row.update(component=identity, split=split)
    return candidates, dict(candidates=len(candidates), source_components=len(components), excluded=dict(excluded),
        splits=dict(Counter(r['split'] for r in candidates)),
        scope='Exact dialogue/seed-family isolation and pattern screen; not semantic deduplication or anonymization proof')


def acquire(root, prior):
    root = private_root(root); prior = private_root(prior)
    if (root / 'acquisition.json').exists(): raise FileExistsError('Immutable fresh acquisition required')
    entries = [fetch(root, 'bst-license.txt', LICENSE_URL, 'CC-BY-4.0', PARLAI, maximum=256*1024),
               fetch(root, 'bst.tar.gz', ARCHIVE_URL, 'CC-BY-4.0', 'BST v1.5', ARCHIVE_SHA, maximum=48*1024**2)]
    license_text = (root / entries[0]['file']).read_text('utf-8')
    if 'Attribution 4.0 International' not in license_text: raise ValueError('Unexpected license evidence')
    # Only old development and standard metadata; final.json is never opened.
    indices, old_hashes = set(), {}
    seal=json.loads((prior/'seal.json').read_text('utf-8'))
    for name in ('development.json', 'standard.json'):
        raw = (prior / name).read_bytes(); old_hashes[name] = hashlib.sha256(raw).hexdigest()
        if seal['files'][name]!=old_hashes[name]:raise ValueError('Prior evaluation metadata differs from its seal')
        data = json.loads(raw)
        if not isinstance(data, list): raise ValueError('Prior corpus must be case list')
        indices.update(r['source_index'] for r in data if r['source'] == 'bst')
    candidates, report = select(episodes((root / entries[1]['file']).read_bytes()), indices)
    save(root / 'acquisition.json', dict(sources=entries, attribution=ATTRIBUTION,
        license='CC-BY-4.0', commercial_and_adaptation='Allowed under attribution and change notice; third-party/privacy rights not waived',
        prior_metadata_hashes=old_hashes, prior_indices=len(indices), final_text_access=False,
        raw_redistribution=False, use='Private editorial source queue, never automatic target acceptance'))
    save(root / 'source-queue.json', candidates); save(root / 'source-summary.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', required=True); p.add_argument('--prior-corpus', required=True)
    a = p.parse_args(); acquire(a.root, a.prior_corpus)
