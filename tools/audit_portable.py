"""Read-only complete Portable membership/size/SHA256 audit. Never repairs.

Reject traversal, aliases and reparse points before opening manifest targets.
CLI accepts only an existing project dist child; reports stay in local_data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import stat


def reparse(path):
    value=path.lstat()
    return stat.S_ISLNK(value.st_mode) or bool(getattr(value,'st_file_attributes',0)&0x400)


def unique(pairs):
    value={}
    for k,v in pairs:
        if k in value:raise ValueError('Duplicate manifest key')
        value[k]=v
    return value


def audit(root):
    root=Path(root)
    if reparse(root):raise ValueError('Reparse build root')
    root=root.resolve();manifest=root/'manifest.json'
    if reparse(manifest) or manifest.stat().st_size>16*1024**2:raise ValueError('Manifest bounds')
    data=json.loads(manifest.read_text('utf-8'),object_pairs_hook=unique)
    if set(data)!={'schema','python','files'} or type(data['schema']) is not int or data['schema']!=1 or not isinstance(data['files'],dict):raise ValueError('Manifest contract')
    files=data['files'];names=set()
    for name,record in files.items():
        parts=PurePosixPath(name).parts
        if (not name or '\\' in name or ':' in name or PurePosixPath(name).is_absolute() or
            name!=PurePosixPath(name).as_posix() or any(p in ('.','..') for p in parts) or name.casefold() in names):raise ValueError('Unsafe manifest path')
        names.add(name.casefold())
        if (not isinstance(record,dict) or set(record)!={'bytes','sha256'} or type(record['bytes']) is not int or record['bytes']<0 or
            not isinstance(record['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',record['sha256'])):raise ValueError('Manifest file contract')
    actual=set()
    def walk_error(error):raise error
    for base,dirs,leaves in os.walk(root,followlinks=False,onerror=walk_error):
        for name in dirs+leaves:
            p=Path(base)/name
            if reparse(p):raise ValueError('Reparse file or directory in build')
        actual.update((Path(base)/name).relative_to(root).as_posix() for name in leaves if Path(base)/name!=manifest)
    missing=sorted(set(files)-actual);extra=sorted(actual-set(files));mismatches=[];forbidden=[];total=0
    for name in sorted(actual&set(files)):
        path=root/name;record=files[name];total+=path.stat().st_size
        parts=PurePosixPath(name.casefold()).parts
        if (parts[0] in ('local_data','.git','.aws','.codex') or path.suffix.lower() in ('.safetensors','.gguf','.token','.key') or
            parts[0]!='runtime' and (path.name.casefold() in ('bootstrap.json','settings.json','companion.sqlite3','sent.sqlite3','.env') or
                                    path.suffix.lower() in ('.sqlite','.sqlite3','.db','.bin','.pt','.pth'))):forbidden.append(name)
        if path.stat().st_size!=record['bytes']:
            mismatches.append(dict(file=name,reason='size'));continue
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024**2),b''):digest.update(chunk)
        if digest.hexdigest()!=record['sha256']:mismatches.append(dict(file=name,reason='sha256'))
    return dict(passed=not (missing or extra or mismatches or forbidden),files=len(files),bytes=total,
                missing=missing,extra=extra,mismatches=mismatches,forbidden=forbidden,
                scope='all manifest files; full hashes; no repair, model loading, UI or network')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[1];target=Path(a.root).absolute();resolved=target.resolve();out=Path(a.output).resolve()
    if not resolved.is_relative_to(repo/'dist') or resolved==repo/'dist' or not out.is_relative_to(repo/'local_data'):raise ValueError('Project build/private output required')
    if out.exists():raise FileExistsError('Preserve earlier audit evidence')
    report=audit(target);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)
