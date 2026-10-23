"""Bounded unauthenticated download of one official comparison model, never ops."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
from dialogue_eval_core import private_root,save


def acquire(root):
    root=private_root(root);root.mkdir(parents=True,exist_ok=True)
    def read(url):
        with urllib.request.urlopen(url,timeout=60) as response:
            data=response.read(4*1024**2+1)
        if len(data)>4*1024**2:raise ValueError('Metadata bound')
        return json.loads(data)
    model='Qwen/Qwen3-8B'
    meta=read('https://huggingface.co/api/models/'+model+'?blobs=true')
    revision=meta['sha']
    files=[r for r in meta['siblings'] if r['rfilename'].endswith('.safetensors') or r['rfilename'] in
           ('config.json','generation_config.json','tokenizer.json','tokenizer_config.json','model.safetensors.index.json','vocab.json','merges.txt','LICENSE','README.md')]
    total=sum(r['size'] for r in files)
    if total>20*1024**3 or shutil.disk_usage(root).free<total+32*1024**3:raise RuntimeError('Disk/download bound')
    saved=[]
    for row in files:
        name=row['rfilename']
        if Path(name).name!=name:raise ValueError('Nested file rejected')
        target=root/name;expected=row.get('lfs',{}).get('sha256')
        if target.exists():
            if target.stat().st_size!=row['size']:raise ValueError('Existing file size mismatch')
        else:
            url=f'https://huggingface.co/{model}/resolve/{revision}/{name}'
            partial=target.with_suffix(target.suffix+'.partial');count=0
            with urllib.request.urlopen(url,timeout=60) as response,partial.open('wb') as out:
                while block:=response.read(1024**2):
                    count+=len(block)
                    if count>row['size']:raise ValueError('Download size exceeded')
                    out.write(block)
            if count!=row['size']:raise ValueError('Incomplete download')
            partial.replace(target)
        h=hashlib.sha256()
        with target.open('rb') as stream:
            while block:=stream.read(8*1024**2):h.update(block)
        if expected and h.hexdigest()!=expected:raise ValueError('Official LFS digest mismatch')
        saved.append(dict(name=name,bytes=row['size'],sha256=h.hexdigest(),official_lfs_sha256=expected))
        save(root/'acquisition.json',dict(model=model,revision=revision,bytes=total,files=saved,authentication=False))
        print(name,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);acquire(p.parse_args().output)
