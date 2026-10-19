"""Read-only, bounded local discovery. Discovery never executes model code."""
from dataclasses import dataclass,asdict,replace
import hashlib
import json
from pathlib import Path
import struct
from itertools import islice
import math
from .paths import MODEL_HOME

OFFICIAL='google/gemma-4-12B-it'

def small_json(path,limit=4*1024**2):
    if path.stat().st_size>limit:raise ValueError('설정 파일이 너무 커요')
    return json.loads(path.read_text(encoding='utf-8'))

@dataclass(frozen=True)
class ModelEntry:
    id:str
    name:str
    path:str
    format:str
    backend:str='Transformers / NF4'
    compatible:bool=False
    reason:str=''
    bytes:int=0
    estimated_vram_gib:int=10
    runtime_verified:bool=False
    def public(self):return asdict(self)

class ModelValidator:
    def validate(self,path):
        p=Path(path).resolve();kind='unknown';size=0;reason='지원하는 모델 설정이 없어요';ok=False
        try:
            if p.is_file() and p.suffix.lower()=='.gguf':
                kind='GGUF';size=p.stat().st_size;reason='GGUF 전용 엔진 미지원'
            elif p.is_file() and p.suffix.lower()=='.safetensors':
                kind='Safetensors';size=p.stat().st_size;reason='단독 가중치예요. config·tokenizer·템플릿을 갖춘 폴더가 필요해요'
            elif (p/'adapter_config.json').is_file():
                kind='PEFT LoRA';reason='어댑터 등록은 아직 지원하지 않아요. 기본 모델과 결합하지 않았어요'
            elif (p/'config.json').is_file():
                kind='Transformers';cfg=small_json(p/'config.json')
                if cfg.get('auto_map'):raise ValueError('외부 Python 코드를 요구하는 모델은 실행하지 않아요')
                if cfg.get('model_type')!='gemma4_unified' or cfg.get('architectures')!=['Gemma4UnifiedForConditionalGeneration']:
                    raise ValueError('현재 검증 경로는 Gemma 4 Unified뿐이에요')
                text=cfg.get('text_config',{})
                if any(type(text.get(k)) is not int or text[k]<=0 for k in ('hidden_size','num_hidden_layers','vocab_size')):raise ValueError('텍스트 모델 설정이 불완전해요')
                # Memory estimate is advisory. Unknown/larger configurations are
                # not promoted merely because their architecture name matches.
                if text.get('hidden_size',0)>4096:raise ValueError('이 크기의 모델은 현재 GPU 경로에서 검증되지 않았어요')
                if cfg.get('quantization_config'):raise ValueError('사전 양자화 형식은 현재 NF4 로더와 호환성을 확인하지 못했어요')
                if not (p/'tokenizer.json').is_file():raise ValueError('tokenizer.json이 없어요')
                tok=small_json(p/'tokenizer_config.json') if (p/'tokenizer_config.json').exists() else {}
                if not (p/'chat_template.jinja').is_file() and not tok.get('chat_template'):raise ValueError('채팅 템플릿이 없어요')
                idx=p/'model.safetensors.index.json'
                names=set(small_json(idx)['weight_map'].values()) if idx.exists() else {'model.safetensors'}
                if not names or len(names)>128:raise ValueError('가중치 목록이 잘못됐어요')
                for name in names:
                    f=(p/name).resolve()
                    # HF snapshots normally link weights to sibling blob paths;
                    # the index itself must still name a plain local shard.
                    if Path(name).name!=name or not f.is_file():raise ValueError('가중치 조각이 없거나 경로가 잘못됐어요')
                    n=f.stat().st_size;size+=n
                    with f.open('rb') as h:
                        raw=h.read(8)
                        if len(raw)!=8:raise ValueError('가중치 헤더가 손상됐어요')
                        length=struct.unpack('<Q',raw)[0]
                        if length>16*1024**2 or length+8>n:raise ValueError('가중치 헤더 길이가 잘못됐어요')
                        header=json.loads(h.read(length));ranges=[]
                        for key,value in header.items():
                            if key=='__metadata__':continue
                            lo,hi=value['data_offsets']
                            if not 0<=lo<=hi<=n-8-length:raise ValueError('가중치 파일이 불완전해요')
                            dtype={'F64':8,'F32':4,'F16':2,'BF16':2,'I64':8,'I32':4,'I16':2,'I8':1,'U8':1,'BOOL':1}.get(value['dtype'])
                            shape=value['shape']
                            if dtype is None or len(shape)>8 or any(type(d) is not int or d<0 for d in shape) or math.prod(shape)*dtype!=hi-lo:raise ValueError('가중치 tensor 크기가 잘못됐어요')
                            ranges.append((lo,hi))
                        if not ranges or max(hi for lo,hi in ranges)!=n-8-length:raise ValueError('가중치 크기가 헤더와 일치하지 않아요')
                        ordered=sorted(ranges)
                        if ordered[0][0]!=0 or any(left[1]!=right[0] for left,right in zip(ordered,ordered[1:])):raise ValueError('가중치 범위가 겹치거나 비어 있어요')
                if size>32*1024**3:raise ValueError('현재 메모리 경로의 지원 크기를 넘어요')
                ok=True;reason='파일 구조 확인 완료 · GPU 최소 추론 검증 후 적용'
        except (OSError,ValueError,KeyError,TypeError,struct.error):
            # No private paths/exception repr in UI or general logs.
            import sys
            exc=sys.exc_info()[1]
            reason=str(exc) if isinstance(exc,ValueError) and str(exc).endswith('요') else '모델 파일을 읽거나 검증하지 못했어요'
        key='local:'+hashlib.sha256(str(p).casefold().encode()).hexdigest()[:24]
        return ModelEntry(key,p.name,str(p),kind,compatible=ok,reason=reason,bytes=size)

class ModelRegistry:
    def __init__(self,roots=None,cache=None):
        self.roots=[Path(p) for p in (roots or [MODEL_HOME])];self.cache=cache;self.entries={}
    def scan(self):
        candidates=[]
        for root in self.roots[:8]:
            if not root.is_dir():continue
            if (root/'config.json').exists() or (root/'adapter_config.json').exists():candidates.append(root)
            try:children=sorted(islice(root.iterdir(),128))
            except OSError:continue
            # Do not list shards twice when the parent is already a model.
            model_root=(root/'config.json').exists() or (root/'adapter_config.json').exists()
            candidates.extend(p for p in children if p.is_dir() and ((p/'config.json').exists() or (p/'adapter_config.json').exists()) or not model_root and p.is_file() and p.suffix.lower() in ('.gguf','.safetensors'))
        try:
            from huggingface_hub.constants import HF_HUB_CACHE
            root=Path(self.cache or HF_HUB_CACHE)/'models--google--gemma-4-12B-it'/'snapshots'
            if root.exists():candidates.extend(sorted(islice(root.iterdir(),16)))
        except (ImportError,OSError):pass
        self.entries={}
        for path in dict.fromkeys(p.resolve() for p in candidates):
            entry=ModelValidator().validate(path)
            if 'models--google--gemma-4-12B-it' in str(path):entry=replace(entry,name='Gemma 4 12B · 기존 캐시')
            self.entries[entry.id]=entry
        return list(self.entries.values())
    def resolve(self,key='base'):
        self.scan()
        if key in ('base','persona','adult'):
            installed=[e for e in self.entries.values() if e.compatible]
            # Official cached weights take precedence over unrelated folders.
            chosen=next((e for e in installed if 'models--google--gemma-4-12B-it' in e.path),None)
            if not chosen:raise ValueError('기본 Gemma 4 파일을 찾지 못했어요. AI 모델에서 폴더를 선택해 주세요')
        else:chosen=self.entries.get(key)
        if not chosen or not chosen.compatible:raise ValueError('선택한 모델을 사용할 수 없어요. 다시 검색해 주세요')
        return chosen
