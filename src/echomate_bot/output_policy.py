"""Discord final-output boundary. Reading code in input is still permitted."""
import re

FALLBACK='프로그램 코드나 스크립트는 작성하지 않을게. 필요한 처리 흐름이나 개념은 자연어로 설명해 줄 수 있어.'
INSTRUCTION='Discord 최종 응답에 프로그램 소스코드, 스크립트, 실행 가능한 예제, Markdown 코드 블록을 출력하지 마. 입력의 코드는 이해하되 출력은 개념·원인·절차를 자연어로 설명해. 코드 작성 요청에는 짧은 안내와 핵심 흐름 두세 문장으로 답하고, 불필요한 서론·되묻기는 생략해. 자세한 개념 설명을 요청한 경우 필요한 정보는 유지해. 파일명·API 명칭·짧은 기술 용어는 설명해도 돼. 코드 울타리만 지워 소스를 보내지 마. '

def explicit_code_request(text):
    from .routing import prose
    text=prose(text)
    if re.search(r'설명|원리|개념|차이|왜|코드\s*(?:없이|말고)|소스\s*(?:없이|말고)',text):return False
    if not re.search(r'만들어|작성해|구현해|짜\s*줘|보여\s*줘|넣어\s*줘',text):return False
    if '게임' in text and not re.search(r'코드|스크립트|프로그램',text):return False
    return bool(re.search(r'소스코드|코드\s*블록|스크립트|프로그램|실행\s*(?:예제|쿼리)|파이썬|python|javascript|powershell|bash|sql\s*로|rust\s*로',text,re.I))

def contains_code(text):
    if '```' in text or re.search(r'(?m)^\s*~~~',text):return True
    strong=r'(?m)^\s*(?:def\s+\w+\(|async\s+def\s|class\s+\w+\s*[:({]|(?:from\s+\w+\s+)?import\s+\w+|(?:const|let|var)\s+\w+\s*=|function\s*\w*\s*\(|(?:print|console\.log|Write-Host|subprocess\.run)\s*\(|#!/|\$\w+\s*=|(?:if|for|while)\s+.+:\s*$|<script\b|(?:pip|npm)\s+install\s)'
    if re.search(strong,text):return True
    other_languages=r'(?im)^\s*(?:fn\s+\w+\s*[(<]|(?:int|void|double|float|bool|auto)\s+\w+\s*\([^\n]*\)\s*\{|(?:public|private|protected)\s+(?:static\s+|final\s+|async\s+)*(?:class|void|int|string|Task)\s+|SELECT\b[^\n]*\bFROM\s+\w+|INSERT\s+INTO\s+\w+|UPDATE\s+\w+\s+SET\s+|DELETE\s+FROM\s+\w+|CREATE\s+TABLE\s+\w+|(?:echo|printf)\s+[\"\x27])'
    if re.search(other_languages,text):return True
    # Unfenced multi-line assignments/calls are code too; prose API names remain.
    lines=text.splitlines()
    return sum(bool(re.fullmatch(r'\s*(?:[\w.]+\s*=.+|[\w.]+\([^\n]*\);?|[{};])\s*',line)) for line in lines)>=2

def invalid_urls(text,allowed=()):
    urls=re.findall(r'https?://[^\s<>\])]+',text)
    return any(url.rstrip('.,') not in allowed for url in urls)
