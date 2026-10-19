"""One ephemeral self-service surface; admin settings live in the Windows app."""
import asyncio
import discord

LABELS={'relationships':'친밀도·호칭 근거','memory':'장기 기억','summaries':'대화 요약'}

class ConsentPanel(discord.ui.View):
    def __init__(self,client,guild,user,choices,counts):
        super().__init__(timeout=300);self.client=client;self.guild=guild;self.user=user
        self.choices=choices;self.counts=counts;self.selected=None;self.confirm=False;self.delete_revision=0;self.lock=asyncio.Lock();self.update_labels()
    async def on_error(self,i,error,item):
        self.client.runtime.note('consent_update_failed_'+type(error).__name__)
        message='처리를 확인하지 못했어. /동의를 다시 열어 현재 상태를 확인해 줘.'
        if i.response.is_done():await i.followup.send(message,ephemeral=True)
        else:await i.response.send_message(message,ephemeral=True)

    def notice(self):
        status='\n'.join(f"{LABELS[k]}: {'켜짐' if self.choices[k] else '꺼짐'} · 보관 {self.counts[k]}건" for k in LABELS)
        return ('**내 데이터 설정 · 이 서버에만 적용**\n'+status+'\n\n'
                '저장 위치: 봇 소유자의 Windows PC `local_data/bot/companion.sqlite3`. PC 소유자는 파일에 접근할 수 있어. 외부 AI 학습으로 전송하지 않아.\n'
                '친밀도: User ID와 연결된 교류 횟수·반응·관계 상태·별명 근거. 변화 이력은 30일, 별명 근거는 90일, 관계 상태·확정 별명은 삭제 전까지 보관해.\n'
                '기억: 민감정보를 제외한 취향·활동·일정. 상태는 기본 6시간, 일정은 종료+유예 뒤 만료해. 목표는 최근 확인 90일 뒤 자동 활용을 보류하며 보류된 목표·취향·직접 기억은 삭제 전까지 남을 수 있어.\n'
                '요약: 여러 턴의 주제·정정·결정·미해결 내용과 출처·참여자·시각·채널. 참여한 사람 모두 요약 저장에 동의한 대화만 저장하며 30일 뒤 만료해. 과거 선별 발췌도 별도로 남아 있을 수 있어.\n'
                '각 항목은 기본 꺼짐이야. 켜도 소유자가 해당 자동 기능을 켠 범위에서만 저장해. **끄기=새 자동 저장·자동 활용 중지, 기존 자료는 유지**. '
                '**삭제=해당 자료와 캐시 제거, 해당 동의도 끔**. 예약 알림은 이 삭제에 포함하지 않아. 자동 백업/삭제 자료 자동 복원은 없어.\n'
                '아래에서 직접 선택해 줘. 다른 서버에는 적용되지 않아.')

    def update_labels(self):
        for item in self.children:
            if getattr(item,'custom_id','').startswith('consent:'):
                key=item.custom_id.split(':')[1];item.label=LABELS[key]+(' 끄기' if self.choices[key] else ' 켜기')

    async def interaction_check(self,i):
        if i.user.id==self.user and i.guild_id==self.guild:return True
        await i.response.send_message('본인 계정의 /동의 화면에서만 변경할 수 있어.',ephemeral=True);return False

    async def change(self,i,key):
        if not await self.interaction_check(i):return
        await i.response.defer()
        async with self.lock:
            desired=not self.choices[key]
            await asyncio.to_thread(self.client.companion.set_consent,self.guild,i.user.id,key,desired,subject=self.user)
            if desired:self.client.runtime.members.clear(self.guild,user=self.user)
            else:self.client.runtime.privacy_changed(self.guild,self.user,key,False)
            self.choices=await asyncio.to_thread(self.client.companion.consent,self.guild,self.user)
            self.counts=await asyncio.to_thread(self.client.companion.data_counts,self.guild,self.user)
            self.update_labels();await i.edit_original_response(content=self.notice(),view=self)

    @discord.ui.button(label='친밀도 켜기',custom_id='consent:relationships',row=0)
    async def relationships(self,i,b):await self.change(i,'relationships')
    @discord.ui.button(label='장기 기억 켜기',custom_id='consent:memory',row=0)
    async def memory(self,i,b):await self.change(i,'memory')
    @discord.ui.button(label='대화 요약 켜기',custom_id='consent:summaries',row=0)
    async def summaries(self,i,b):await self.change(i,'summaries')
    @discord.ui.select(placeholder='삭제할 내 자료 선택 · 동의 끄기와 달라요',options=[discord.SelectOption(label=v,value=k) for k,v in LABELS.items()],row=1)
    async def choose_delete(self,i,select):
        if not await self.interaction_check(i):return
        selected=select.values[0]
        await i.response.defer()
        async with self.lock:
            self.selected=selected;self.confirm=False;self.delete_revision+=1;self.delete.label='선택 자료 삭제'
            await i.edit_original_response(content=self.notice(),view=self)
    @discord.ui.button(label='선택 자료 삭제',style=discord.ButtonStyle.danger,row=2)
    async def delete(self,i,button):
        if not await self.interaction_check(i):return
        selected,confirmed,revision=self.selected,self.confirm,self.delete_revision
        await i.response.defer()
        async with self.lock:
            if revision!=self.delete_revision or selected!=self.selected:
                await i.edit_original_response(content=self.notice()+'\n선택이 바뀌었어. 삭제할 종류를 다시 확인해 줘.',view=self);return
            if not selected:
                await i.edit_original_response(content=self.notice()+'\n먼저 삭제할 종류를 선택해 줘.',view=self);return
            if not confirmed:
                self.confirm=True;button.label='삭제 확인 · '+LABELS[selected]
                await i.edit_original_response(content=self.notice()+'\n선택한 자료를 삭제하려면 삭제 확인을 눌러 줘.',view=self);return
            await asyncio.to_thread(self.client.companion.delete_personal,self.guild,i.user.id,selected)
            self.client.runtime.privacy_changed(self.guild,self.user,selected,True)
            self.choices=await asyncio.to_thread(self.client.companion.consent,self.guild,self.user)
            self.counts=await asyncio.to_thread(self.client.companion.data_counts,self.guild,self.user)
            self.confirm=False;self.delete_revision+=1;button.label='선택 자료 삭제';self.update_labels()
            await i.edit_original_response(content=self.notice()+'\n선택한 자료를 삭제했어.',view=self)

async def open_consent(client,i):
    if not i.guild_id or str(i.guild_id) not in client.settings.get()['guilds']:
        await i.response.send_message('등록된 서버에서 본인 데이터 설정을 열어 줘.',ephemeral=True);return
    await i.response.defer(ephemeral=True)
    choices=await asyncio.to_thread(client.companion.consent,i.guild_id,i.user.id)
    counts=await asyncio.to_thread(client.companion.data_counts,i.guild_id,i.user.id)
    view=ConsentPanel(client,i.guild_id,i.user.id,choices,counts)
    await i.followup.send(view.notice(),view=view,ephemeral=True)
