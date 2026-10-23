"""Known embodiment limit, not a classifier for addressees or user memories."""
import re


def physical_recollection(text):
    if not isinstance(text,str):return False
    text=' '.join(text.split())
    text=re.sub(r'"[^"\n]*"|“[^”\n]*”|「[^」\n]*」', '',text)
    # Fiction is allowed, but an explicit reality claim cannot borrow its proof.
    if not re.search(r'실제|현실|진짜로',text) and re.search(r'가상|설정|역할극|극중|소설|이야기 속',text):return False
    addressed=re.search(r'너랑|너와|네가|너도|네 말|네 기억',text)
    physical=re.search(r'(?:같이|함께|우리|너랑|너와).{0,60}(?:갔|먹었|마셨|만났|걸었|여행했|산책했|일했)|(?:갔|먹었|마셨|만났|걸었|여행했|산책했|일했).{0,40}(?:너랑|너와|네가|너도)',text)
    recall=re.search(r'기억|그때|지난번|예전에|추억|떠올',text)
    return bool(addressed and physical and recall)


def grounded_reply(context,cfg):
    from .character_card import spoken_users
    users=spoken_users(context)
    latest=cfg.get('_current_utterance',users[-1] if users else None)
    if not physical_recollection(latest):return None
    from .character_profiles import applied_profile
    if applied_profile(cfg)['speech']=='polite':return '저는 실제 몸으로 함께 다니거나 경험한 과거가 없어서 그런 기억이 있다고 할 수는 없어요. 가상 설정 속 이야기라면 현실 경험과 구분해서 이어갈 수 있어요.'
    return '나는 실제 몸으로 같이 다니거나 경험한 과거가 없어서 그런 기억이 있다고 할 수는 없어. 가상 설정 속 이야기라면 현실 경험과 구분해서 이어갈 수 있어.'
