"""Small counterbalanced CPU dispatch thread timing, same GPU/text inputs.

Private outputs only. Does not train or change the selected model.
"""
import argparse,asyncio,hashlib,json,time
from pathlib import Path
from echomate_bot.inference import LocalBackend
from echomate_bot.character import instruction
from echomate_bot.settings import DEFAULTS,private_path

async def run(root):
    root.mkdir(parents=True,exist_ok=False)
    backend=LocalBackend();await backend.ready()
    import torch
    original=torch.get_num_threads();rows=[]
    messages=[dict(role='system',content=instruction(DEFAULTS)),dict(role='user',content='파이썬 리스트 얕은 복사와 깊은 복사의 차이를 두 문장으로 알려 줘.')]
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/echomate_bot').glob('*.py')}
    (root/'manifest.json').write_text(json.dumps(dict(original_threads=original,source_sha256=sources,synthetic=True,sequence=['warmup','default',4,'default',4]),indent=2),encoding='utf-8')
    try:
        for index,threads in enumerate((original,original,4,original,4)):
            await asyncio.get_running_loop().run_in_executor(backend.executor,torch.set_num_threads,threads)
            torch.manual_seed(2026);started=time.monotonic()
            answer=await backend._job(messages,budget=256,weight='persona')
            rows.append(dict(warmup=index==0,threads=threads,seconds=round(time.monotonic()-started,3),metric=backend.metrics[-1],response=answer,sha256=hashlib.sha256(answer.encode()).hexdigest()))
            (root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        torch.set_num_threads(original);await backend.close()
    print(json.dumps([dict(warmup=r['warmup'],threads=r['threads'],seconds=r['seconds'],tokens=r['metric']['output_tokens']) for r in rows]),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(private_path(parser.parse_args().output)))
