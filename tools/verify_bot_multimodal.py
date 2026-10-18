"""Synthetic local GPU compatibility probe; no Discord token or real messages."""
import asyncio
import argparse
from io import BytesIO
import json
from pathlib import Path
import subprocess
import time
from PIL import Image,ImageDraw
from echomate_bot.inference import LocalBackend
from echomate_bot.settings import DEFAULTS
from echomate_bot.vision import frames,parse_visual


async def run(root):
    root.mkdir(exist_ok=False,parents=True)
    backend=LocalBackend();rows=[];started=time.monotonic()
    a=Image.new('RGB',(320,240),'white');d=ImageDraw.Draw(a)
    d.rectangle((30,70,120,170),fill='red');d.ellipse((190,70,290,170),fill='blue')
    b=Image.new('RGB',(320,240),'white');ImageDraw.Draw(b).rectangle((200,70,290,170),fill='red')
    a.save(root/'static.png');a.save(root/'moving.gif',save_all=True,append_images=[b],duration=[350,350],loop=0)
    try:
        for weight in ('base','persona'):
            for name in ('static.png','moving.gif'):
                images,metadata=frames((root/name).read_bytes())
                try:
                    answer=await backend.visual(images,metadata,weight=weight)
                    (root/(weight+'-'+name+'.raw.json')).write_text(json.dumps(dict(response=answer),ensure_ascii=False),encoding='utf-8')
                    parsed=parse_visual(answer)
                    rows.append(dict(weight=weight,asset=name,ok=True,analysis=parsed,metrics=backend.metrics[-1]))
                except Exception as exc:rows.append(dict(weight=weight,asset=name,ok=False,error_type=type(exc).__name__,metrics=backend.metrics[-1:]));raise
                (root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            cfg=dict(DEFAULTS,model=weight)
            answer=await backend.text([dict(role='user',content='파이썬에서 리스트를 b=a.copy()로 복사하면 바깥 리스트도 같은 객체야? 짧게 정확히 설명해 줘.')],cfg)
            rows.append(dict(weight=weight,asset='text',ok=True,response=answer,metrics=backend.metrics[-1]))
            (root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        (root/'summary.json').write_text(json.dumps(dict(status='finished',seconds=round(time.monotonic()-started,1),
            processor=backend.processor_origin,conditions=len(rows),metrics=backend.metrics),indent=2),encoding='utf-8')
    except Exception as exc:
        (root/'failure.json').write_text(json.dumps(dict(type=type(exc).__name__,completed=len(rows),seconds=round(time.monotonic()-started,1))),encoding='utf-8')
        raise
    finally:await backend.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    from echomate_bot.settings import private_path
    asyncio.run(run(private_path(parser.parse_args().output)))
