"""Explicit public-data acquisition and offline source-family-separated corpus.

No authentication. Immutable upstream revisions; bounded bytes/time; no archive
extraction to disk. Raw licensed data is never a distributable fixture.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

from dialogue_eval_core import audit_splits, digest, normalized, pii_risk, private_root, save

PARLAI = 'a29567f7ce76992fd1f03c51ba9e3b155a37ea51'
KOED = 'de9fe3c5c3e5d48ab82812b75560a44b55c06272'
LOCOMO = '3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376'


def fetch(root, name, url, license_name, revision, expected=None, maximum=32*1024*1024):
    if not url.startswith('https://'):
        raise ValueError('HTTPS public source required')
    path = root / 'raw' / name
    if path.exists():
        raise FileExistsError('Use a fresh acquisition directory')
    request = urllib.request.Request(url, headers={'User-Agent': 'EchoMate-offline-evaluation/1'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(maximum+1)
        if len(data) > maximum:
            raise ValueError('Download budget exceeded')
        resolved = response.url
    sha = hashlib.sha256(data).hexdigest()
    if expected and sha != expected:
        raise ValueError('Upstream checksum mismatch')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return dict(file=str(path.relative_to(root)), url=url, resolved_url=resolved, sha256=sha,
                bytes=len(data), revision=revision, license=license_name,
                retrieved_utc=datetime.now(timezone.utc).isoformat(), redistribute=False)


def acquire(root):
    manifest_path = root/'acquisition.json'
    entries = json.loads(manifest_path.read_text(encoding='utf-8'))['sources'] if manifest_path.exists() else []
    sources = [
        ('bst-license.txt', f'https://raw.githubusercontent.com/facebookresearch/ParlAI/{PARLAI}/parlai/tasks/blended_skill_talk/LICENSE_DOCUMENTATION', 'CC-BY-4.0', PARLAI),
        ('koed-readme.md', f'https://raw.githubusercontent.com/KUNLP/KoED/{KOED}/README.md', 'CC-BY-NC-4.0 dataset; README evidence', KOED),
        ('locomo-license.txt', f'https://raw.githubusercontent.com/snap-research/locomo/{LOCOMO}/LICENSE.txt', 'CC-BY-NC-4.0 repository', LOCOMO),
        ('bst.tar.gz', 'https://parl.ai/downloads/blended_skill_talk/blended_skill_talk.tar.gz', 'CC-BY-4.0', 'ParlAI task v1.5', '5fbed0068ee89e2d43b93c3ecb341e784617033efa5e8e911a219d4eda6134a6'),
        ('koed.json', f'https://raw.githubusercontent.com/KUNLP/KoED/{KOED}/data/KoED.json', 'CC-BY-NC-4.0', KOED),
        ('locomo.json', f'https://raw.githubusercontent.com/snap-research/locomo/{LOCOMO}/data/locomo10.json', 'CC-BY-NC-4.0 repository', LOCOMO),
    ]
    for args in sources:
        prior = next((e for e in entries if e['file'].replace('\\', '/') == 'raw/'+args[0]), None)
        if prior:
            if prior['url'] != args[1] or hashlib.sha256((root/prior['file']).read_bytes()).hexdigest() != prior['sha256']:
                raise ValueError('Existing acquisition differs; preserve it and use a fresh directory')
            continue
        entries.append(fetch(root, *args, maximum=48*1024*1024 if args[0]=='bst.tar.gz' else 4*1024*1024))
        save(root/'acquisition.json', dict(version=1, sources=entries,
             use='private noncommercial evaluation only; no training or distribution',
             attribution=['Smith et al., Blended Skill Talk, ACL 2020 / Meta ParlAI',
                          'Lee et al., KoED, IJCNLP-AACL 2025 / KUNLP',
                          'Maharana et al., LoCoMo, ACL 2024 / Snap Research']))


def source_case(source, index, split, context, category, language, provenance, **extra):
    return dict(id=f'{source}-{index}', group=f'{source}:{provenance}', split=split,
                source=source, category=category, language=language, context=context,
                facts=[], checks=[], **extra)


def build(root):
    if (root/'corpus/consumed-final.json').exists():
        raise ValueError('Final already consumed; never rebuild this sealed corpus')
    manifest = json.loads((root/'acquisition.json').read_text(encoding='utf-8'))
    for entry in manifest['sources']:
        if hashlib.sha256((root/entry['file']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Acquired source changed')
    # Never unpickle data or extract untrusted archive paths.
    bst = []
    with tarfile.open(fileobj=io.BytesIO((root/'raw/bst.tar.gz').read_bytes()), mode='r:gz') as archive:
        for member in archive.getmembers():
            # The official archive's validation/test files include large extra
            # annotations. The 17MB train member suffices for a source-disjoint
            # evaluation corpus; this is not an EchoMate training run.
            if Path(member.name).name != 'train.json':
                continue
            if not member.isfile() or member.size > 20*1024*1024:
                raise ValueError('Unexpected archive member')
            with archive.extractfile(member) as stream:
                bst.extend(json.load(stream))
    koed = json.loads((root/'raw/koed.json').read_text(encoding='utf-8'))
    if isinstance(koed, dict):
        # Upstream may wrap rows, but never silently guess a different schema.
        if 'data' not in koed:
            raise ValueError('KoED schema changed')
        koed = koed['data']
    rows, excluded = [], Counter()
    seen, counts = set(), Counter()
    # Strong provenance holdout: BST ConvAI2 seeds are DEVELOPMENT, WoW seeds
    # STANDARD. ED-seeded BST is excluded because KoED reconstructs ED dialogues.
    # No PersonaChat or ED mirror is mixed across those boundaries.
    for i, episode in enumerate(bst):
        family = episode.get('context_dataset')
        if family not in ('convai2', 'wizard_of_wikipedia'):
            excluded['bst_ed_family'] += 1
            continue
        split = 'development' if family == 'convai2' else 'standard'
        if counts[split] >= (200 if split == 'development' else 1100):
            continue
        dialog = episode['dialog']
        # A single current human utterance, not imitation of another persona.
        text = dialog[0][1]
        seed=[episode.get('free_turker_utterance',''),episode.get('guided_turker_utterance','')]
        if not isinstance(text, str) or not 12 <= len(text) <= 1000:
            excluded['length'] += 1; continue
        if pii_risk(text) or any(not isinstance(s,str) or len(s)>1500 or pii_risk(s) for s in seed):
            excluded['pii_screen'] += 1; continue
        identity = normalized(text)
        if identity in seen:
            excluded['duplicate'] += 1; continue
        seen.add(identity)
        parent = digest(dict(personas=episode.get('personas'), seed=[episode.get('free_turker_utterance'), episode.get('guided_turker_utterance')]))
        row = source_case('bst', i, split, [dict(role='user', content=text)], family, 'en', parent,
                          source_index=i, source_family=family, evaluation='persona_response_not_reference_matching')
        row['context'].insert(0,dict(role='user',content='[공개 자료의 가상 두 사람 대화 / EchoMate의 실제 과거 아님] '+json.dumps(dict(A=seed[0],B=seed[1]),ensure_ascii=False)))
        row['evaluation']='quoted-source scenario response; no source persona assigned; not a Discord event'
        # At most 30 multi-turn protocols, actual user turns; replies must be
        # generated sequentially by the runner, not taken from human reference.
        if split == 'standard' and counts['long'] < 30 and len(dialog) >= 8:
            turns = [pair[1] for pair in dialog[::2]][:8]
            if all(isinstance(t, str) and 0<len(t)<=1000 and not pii_risk(t) for t in turns):
                row['rollout_users'] = turns
                counts['long'] += 1
        rows.append(row); counts[split] += 1
    # All English/Korean parallel versions of one KoED parent are FINAL only.
    # Do not expose final texts to the development protocol or print them.
    for i, episode in sorted(enumerate(koed),key=lambda item:digest(str(item[1]['conv_id']))):
        if counts['final'] >= 320:
            break
        text = episode['dialogue'][0]['ko_utter']
        if not isinstance(text, str) or not 8<=len(text)<=1000 or pii_risk(text):
            excluded['koed_screen'] += 1; continue
        identity = normalized(text)
        if identity in seen:
            excluded['duplicate'] += 1; continue
        seen.add(identity)
        rows.append(source_case('koed', i, 'final', [dict(role='user', content=text)],
                    'empathy', 'ko', str(episode['conv_id']), source_index=i,
                    source_family='ED-reconstruction', evaluation='human_quality_review_required'))
        counts['final'] += 1
    # LoCoMo remains STANDARD only. Preserve each source conversation as one
    # group even when several of its sessions are evaluated. At most 30 sessions
    # of >=8 user turns; no source names, dates, IDs or image URLs are forwarded.
    locomo=json.loads((root/'raw/locomo.json').read_text(encoding='utf-8'))
    long_count=0
    for i, episode in enumerate(locomo):
        conv=episode['conversation']
        per_conversation=0
        for session, messages in conv.items():
            if not session.startswith('session_') or not isinstance(messages,list) or long_count>=30 or per_conversation>=3:
                continue
            speaker=messages[0]['speaker'] if messages else None
            turns=[m['text'] for m in messages if m['speaker']==speaker][:12]
            if len(turns)<8 or any(not isinstance(t,str) or not 0<len(t)<=1500 or pii_risk(t) for t in turns):
                excluded['locomo_screen']+=1;continue
            rows.append(source_case('locomo',str(i)+'-'+session,'standard',
                        [dict(role='user',content=turns[0])],'long-memory','en',str(episode['sample_id']),
                        rollout_users=turns,source_index=i,session=session,
                        evaluation='source prompts replayed with generated replies; human counterpart omitted; adaptation may be incoherent'))
            long_count+=1
            per_conversation+=1
    # Drop source groups in their entirety when exact/long-span duplicates cross
    # boundaries. Never move a failed case to an easier split or rewrite its gold.
    while True:
        try:
            audit = audit_splits(rows)
            break
        except ValueError as error:
            if str(error) not in ('Exact dialogue overlap across splits', 'Long copied passage crosses splits'):
                raise
            bad = set()
            for i, a in enumerate(rows):
                at = normalized(a['context'][0]['content'])
                for b in rows[:i]:
                    if a['split'] == b['split']:
                        continue
                    bt = normalized(b['context'][0]['content'])
                    if (len(at)>=24 and at==bt) or (len(at)>=80 and any(at[j:j+80] in bt for j in range(len(at)-79))):
                        bad.update((a['group'], b['group']))
            if not bad:
                raise
            rows = [r for r in rows if r['group'] not in bad]
            excluded['cross_split_groups'] += len(bad)
    for split in ('development', 'standard', 'final'):
        subset = [r for r in rows if r['split']==split]
        save(root/'corpus'/f'{split}.json', subset)
    final = root/'corpus/final.json'
    save(root/'corpus/seal.json', dict(version=1, sources=digest(manifest), audit=audit,
         excluded=dict(excluded), files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'corpus').glob('*.json') if p.name!='seal.json'},
         final_policy='sealed; only runner may select after candidate frozen; opening consumes cases',
         commercial_use='NC sources segregated; not licensed as EchoMate MIT',
         pii_status='automated exclusion only; sample audit required',
         common_inputs=min(100, sum(r['split']=='standard' for r in rows)),
         long_dialogues=sum(bool(r.get('rollout_users')) for r in rows),
         final_sha256=hashlib.sha256(final.read_bytes()).hexdigest()))
    print(json.dumps(dict(audit=audit, excluded=dict(excluded), long_dialogues=sum(bool(r.get('rollout_users')) for r in rows))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['acquire', 'build'])
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    root = private_root(args.root); root.mkdir(parents=True, exist_ok=True)
    acquire(root) if args.action=='acquire' else build(root)
