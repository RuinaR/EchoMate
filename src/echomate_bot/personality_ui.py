"""Owner-only, ephemeral applied settings view; no inference or private store."""
import re
import discord
from .character_profiles import applied_profile,APPROACHES

def display(value):
    value=str(value)
    if re.search(r'(?:[A-Za-z]:[\\/]|/(?:home|Users|tmp)/|\d{16,}|<@|(?:token|password|api[_ -]?key)\s*[:=]|[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,})',value,re.I):return '민감할 수 있는 표시 자료는 생략했어'
    return discord.utils.escape_markdown(value.replace('@','＠'))

def personality_embed(cfg):
    p=applied_profile(cfg)
    embed=discord.Embed(title='🎭 현재 적용된 캐릭터',description=display(p['introduction']),colour=0x9b91ff)
    embed.add_field(name='캐릭터',value=display(p['name']),inline=False)
    embed.add_field(name='핵심 접근 방식',value=APPROACHES[p['approach']],inline=False)
    strategies={'balanced':'상황을 짚고 필요한 관점을 제안해.','supportive':'공감과 선택권을 먼저, 부담을 줄이는 관점을 제안해.','playful':'가벼운 비유와 놀이 관점으로 반응해. 심각한 고통에는 장난을 멈춰.','analytical':'원인·조건을 구분하고 다음 행동을 제안해.','dry':'결론과 현실적인 선택부터, 사람을 비웃지 않는 건조한 유머를 써.'}
    embed.add_field(name='상황별 반응',value=strategies[p['approach']],inline=False)
    embed.add_field(name='말투·길이',value=('반말' if p['speech']=='casual' else '존댓말')+' · '+('짧게' if p['length']=='short' else '상황에 맞게')+' · 설명 '+{'brief':'간단히','balanced':'균형 있게','detailed':'자세히'}[p['detail']],inline=False)
    embed.add_field(name='현재 설정 기분',value=p['mood']+(' · 자동 연출 켜짐(각 발언에서만 달라질 수 있어)' if cfg['auto_mood'] else ''),inline=False)
    embed.add_field(name='실제 적용 수치',value='\n'.join(f'{label}: {p[key]}/100' for key,label in [('energy','에너지'),('warmth','다정함'),('calmness','차분함'),('playfulness','장난기'),('honesty','솔직함'),('humor','유머'),('curiosity','호기심'),('skepticism','전제 점검'),('cuteness','귀여움'),('exclamation','감탄'),('emoji','텍스트 이모지')]),inline=False)
    for key,label in [('tastes','취향'),('values','가치관'),('habits','대화 습관')]:
        if p[key]:embed.add_field(name=label,value=display(p[key]),inline=False)
    embed.set_footer(text='조회 시점에 저장·적용된 설정이야. 성격은 지속 성향, 기분은 현재 표현 상태야. 편집 중인 값은 포함하지 않아.')
    return embed

async def open_personality(client,i):
    try:client.settings.authorize(i.user.id)
    except PermissionError:
        await i.response.send_message('이 명령은 봇 소유자만 사용할 수 있어.',ephemeral=True);return
    if i.guild_id is None:
        await i.response.send_message('서버에서 확인해 줘.',ephemeral=True);return
    await i.response.send_message(embed=personality_embed(client.settings.get()),ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
