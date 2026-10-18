"""Interactive local setup never prints or accepts a bot token on argv."""
import argparse
import asyncio
import getpass
import json
import logging
import os
import secrets
import subprocess
from .settings import ROOT,Settings,positive_id


def setup():
    path=ROOT/"bootstrap.json"
    if path.exists():raise SystemExit("이미 로컬 비밀 설정이 있어. 덮어쓰지 않았어.")
    owner=positive_id(int(input("소유자 Discord User ID: ").strip()))
    guild=positive_id(int(input("테스트 서버 ID: ").strip()))
    channel=positive_id(int(input("허용할 테스트 채널 ID: ").strip()))
    token=getpass.getpass("공식 Bot Token (화면에 표시되지 않음): ").strip()
    if not token or any(c.isspace() for c in token):raise SystemExit("잘못된 토큰 형식")
    ROOT.mkdir(parents=True,exist_ok=True)
    if os.name=="nt":
        # Windows account is the security boundary; remove inherited broad access.
        identity=subprocess.check_output(["whoami"],text=True).strip()
        subprocess.run(["icacls",str(ROOT),"/inheritance:r","/grant:r",identity+":(OI)(CI)F","SYSTEM:(OI)(CI)F"],check=True,capture_output=True)
    key=secrets.token_hex(32)
    path.write_text(json.dumps(dict(owner_id=owner,token=token,admin_guilds=[guild],signing_key=key)),encoding="utf-8")
    settings=Settings(owner,key)
    settings.set_scope(owner,guild,channel,"mention")
    print("저장 완료. 기본은 정지 상태야. 시작 후 /echo panel, /echo set key:enabled value:true로 테스트 채널만 켜 줘.")


async def run():
    from .instance import InstanceLease
    lease=InstanceLease()
    from .inference import LocalBackend
    from .discord_app import EchoClient
    path=ROOT/"bootstrap.json"
    if not path.exists():raise SystemExit("먼저 tools/setup_discord_bot.ps1을 실행해 줘.")
    bootstrap=json.loads(path.read_text(encoding="utf-8"))
    settings=Settings(bootstrap['owner_id'],bootstrap['signing_key'])
    if not bootstrap['admin_guilds'] or any(type(g) is not int or g<=0 for g in bootstrap['admin_guilds']):raise ValueError("Invalid management guilds")
    # Library HTTP loggers can include request URLs. Keep only private minimal codes.
    logging.getLogger("discord").setLevel(logging.CRITICAL)
    client=EchoClient(settings,LocalBackend(),bootstrap['admin_guilds'])
    try:
        await client.backend.ready()
        await client.start(bootstrap['token'],reconnect=True)
    finally:
        ROOT.mkdir(parents=True,exist_ok=True)
        (ROOT/"diagnostics.json").write_text(json.dumps(client.runtime.diagnostics,indent=2),encoding="utf-8")
        (ROOT/"performance.json").write_text(json.dumps(client.backend.metrics,indent=2),encoding="utf-8")
        if not client.is_closed():await client.close()
        lease.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--setup',action='store_true')
    args=parser.parse_args()
    try:
        if args.setup:setup()
        else:asyncio.run(run())
    except KeyboardInterrupt:pass
    except Exception as exc:
        # Never print repr(exc), HTTP request objects, bootstrap or prompt text.
        raise SystemExit("시작/연결을 중단했어 ("+type(exc).__name__+"). 로컬 설정과 실행 안내를 확인해 줘.") from None


if __name__=='__main__':main()
