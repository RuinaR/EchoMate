"""Local first-run setup. No network, no overwrite, Windows account-bound secrets."""
import base64
import ctypes
import json
import os
import secrets
from pathlib import Path

def protect(value,decrypt=False):
    if os.name!='nt':raise RuntimeError('Windows 보안 저장소가 필요해요')
    from ctypes import wintypes
    class Blob(ctypes.Structure):_fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    raw=base64.b64decode(value) if decrypt else value.encode('utf-8')
    buf=ctypes.create_string_buffer(raw);source=Blob(len(raw),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte)));result=Blob()
    fn=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(result)):raise OSError('Windows 비밀 저장 실패')
    try:
        value=ctypes.string_at(result.data,result.size)
        return value.decode('utf-8') if decrypt else base64.b64encode(value).decode('ascii')
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes=[wintypes.HLOCAL]
        ctypes.windll.kernel32.LocalFree(ctypes.cast(result.data,wintypes.HLOCAL))

def load_bootstrap(path):
    envelope=json.loads(Path(path).read_text(encoding='utf-8'))
    return json.loads(protect(envelope['protected'],True)) if set(envelope)=={'protected','version'} and envelope['version']==1 else envelope

def create_installation(path,owner,token,admin_guilds=()):
    from .settings import positive_id
    positive_id(owner);path=Path(path)
    if not isinstance(token,str) or not 20<=len(token)<=256 or any(c.isspace() for c in token):raise ValueError('Bot Token 형식을 확인해 주세요')
    for guild in admin_guilds:positive_id(guild)
    data=dict(owner_id=owner,token=token,admin_guilds=list(admin_guilds),signing_key=secrets.token_hex(32))
    envelope=dict(version=1,protected=protect(json.dumps(data)))
    path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive create prevents accidental replacement of existing credentials.
    with path.open('x',encoding='utf-8') as handle:json.dump(envelope,handle)
    return data

GUIDE='''1. Discord Developer Portal에서 본인 애플리케이션과 Bot을 만드세요.
2. Bot → Message Content Intent를 켜세요. Members/Presence Intent는 필요 없어요.
3. OAuth2에서 bot·applications.commands를 선택해 본인 서버에 초대하세요.
4. 채널 보기·기록 보기·메시지 보내기·반응 추가·스레드 메시지 권한만 허용하세요.
5. 본인의 Discord 사용자 ID와 Bot Token을 아래에 입력하세요.
토큰은 현재 Windows 계정에 암호화해 저장해요. 채팅·진단에 넣지 마세요.
저장 후 AI 모델에서 Gemma 4 폴더를 확인하고 캐릭터를 고르세요.
직접 목록 새로고침을 누른 뒤 허용 채널을 저장해야 봇이 말할 수 있어요.
EchoMate는 사용자가 시작하기 전에는 Discord에 연결하지 않아요.'''
