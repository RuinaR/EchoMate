"""User-invoked, isolated offline UI check. Never opens a real Discord session.

Environment selection happens before importing desktop/settings. The main app
and its stored credentials are unchanged; synthetic metadata is labelled.
"""
import os
from pathlib import Path

def configure_environment():
    base=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'EchoMate'
    home=Path(os.environ.get('ECHOMATE_CHECK_HOME',base/'manual-check')).resolve()
    if home in {(base/'local_data').resolve(),(Path.cwd()/'local_data').resolve()}:
        raise ValueError('Offline check must not use operating data')
    os.environ['ECHOMATE_DATA_HOME']=str(home)
    os.environ['ECHOMATE_DISTRIBUTED']='1'
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    return home

def controller_type(base):
    class OfflineController(base):
        async def command(self,operation,**kwargs):
            if operation in ('start','refresh','command_review','command_apply') or operation=='visual_cache' and kwargs.get('refresh'):
                self.error='오프라인 검증에서는 Discord 연결·조회·전송을 하지 않아요.'
                self._publish()
                return dict(ok=False,error=self.error)
            return await super().command(operation,**kwargs)
        def _publish(self):
            # Fixture metadata, never downloaded or presented as a real guild.
            self.inventory=[dict(id=2,label='검증 예시 서버 · 실제 Discord 아님',channels=[
                dict(id=3,label='가상 채널 · 송신 안 함',thread=False),
                dict(id=7,label='가상 스레드 · 송신 안 함',thread=True,parent=3)])]
            return super()._publish()
    return OfflineController

def main():
    home=configure_environment()
    import sys
    # Never reinterpret an already-running operating installation in place.
    # The VBS entry starts a fresh Python process; embedded callers must too.
    settings=sys.modules.get('echomate_bot.settings')
    paths=sys.modules.get('echomate_bot.paths')
    if settings is not None and settings.ROOT.parent.resolve()!=home or paths is not None and paths.DATA_HOME.resolve()!=home:
        raise RuntimeError('Offline check requires a fresh isolated process')
    home.mkdir(parents=True,exist_ok=True)
    if sys.stderr is None:sys.stderr=(home/'offline-check-console.log').open('a',encoding='utf-8')
    if sys.stdout is None:sys.stdout=sys.stderr
    import discord
    async def forbidden(*args,**kwargs):raise RuntimeError('Discord disabled in offline check')
    discord.Client.login=forbidden;discord.Client.start=forbidden;discord.http.HTTPClient.request=forbidden
    from .desktop import LocalController,DesktopApp,tk
    class CheckApp(DesktopApp):
        def render(self):
            super().render()
            self.root.title('EchoMate · 오프라인 검증 · 운영 자료와 분리됨')
        def setup_credentials(self):
            self.form('오프라인 검증용 가짜 정보',[
                ('owner','가상 사용자 ID · 그대로 사용','1'),
                ('token','가짜 토큰 · 실제 토큰을 넣지 마세요','offline-synthetic-token-not-for-discord')],
                lambda v:self.controller.submit('setup',owner=v['owner'],token=v['token']),
                '검증 전용 저장소예요. 실제 봇 계정이나 토큰 없이 창·저장·모델·캐릭터를 확인할 수 있어요.')
    root=tk.Tk();CheckApp(root,controller_type(LocalController)());root.mainloop()

if __name__=='__main__':main()
