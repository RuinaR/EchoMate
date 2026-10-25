"""Read-only current character command, no inference/private-store access."""
import discord
from .personality_ui import display


async def open_character(client, interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message('서버에서 현재 캐릭터 정보를 확인해 줘.',ephemeral=True)
        return
    runtime=client.runtime
    backend=runtime.backend
    entry=getattr(backend,'entry',None)
    if not getattr(backend,'character_id',None) or entry is None:
        await interaction.response.send_message('현재 사전 학습 캐릭터 정보가 없어.',ephemeral=True)
        return
    state=('복구 필요' if getattr(runtime,'character_transition_state',None)=='RecoveryRequired'
           else '전환 중' if runtime.changing_model else '실행 오류' if backend.failed
           else 'GPU 로딩됨 · 의미 판단 검증 미완료' if backend.model is not None and not getattr(backend,'capabilities_verified',False)
           else '모델 준비됨 · 제품 품질 검증은 별도' if backend.model is not None else '모델 미로딩')
    embed=discord.Embed(title='현재 캐릭터',description=display(entry.description),colour=0x9B91FF)
    embed.add_field(name='이름',value=display(backend.name),inline=False)
    embed.add_field(name='상태',value=state,inline=False)
    embed.add_field(name='모델 계열',value=display(entry.base_dependency),inline=False)
    embed.set_footer(text='캐릭터·이름 변경은 Windows 관리자 앱에서만 할 수 있어.')
    await interaction.response.send_message(embed=embed,ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
