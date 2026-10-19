"""Static UI callback inventory. This is not an execution/coverage certificate."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def inventory(root):
    sources=[root/'src/echomate_bot'/name for name in ('desktop_ui.py','companion_ui.py','user_check.py')]
    trees={path:ast.parse(path.read_text(encoding='utf-8')) for path in sources}
    methods={node.name for tree in trees.values() for cls in ast.walk(tree) if isinstance(cls,ast.ClassDef) for node in cls.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
    controls=[]
    for path,tree in trees.items():
        for cls in ast.walk(tree):
            if not isinstance(cls,ast.ClassDef):continue
            for method in cls.body:
                if not isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
                for call in ast.walk(method):
                    if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Attribute) or not isinstance(call.func.value,ast.Name) or call.func.value.id!='self':continue
                    kind=call.func.attr
                    layout={'button':(4,5),'toggle':(2,4),'choices':(2,4),'form':(0,2)}
                    if kind not in layout:continue
                    label_index,callback_index=layout[kind]
                    if len(call.args)<=callback_index:continue
                    label=call.args[label_index];callback=call.args[callback_index]
                    label=label.value if isinstance(label,ast.Constant) and isinstance(label.value,str) else '동적 항목 · 소스 참조'
                    refs={n.attr for n in ast.walk(callback) if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='self' and n.attr in methods}
                    controls.append(dict(file=path.relative_to(root).as_posix(),line=call.lineno,method=method.name,kind=kind,label=label,callbacks=sorted(refs)))
    return controls


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--evidence');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];output=Path(args.output).resolve();output.relative_to(root/'docs')
    rows=inventory(root)
    observations={}
    if args.evidence:
        path=Path(args.evidence).resolve();path.relative_to(root/'local_data')
        evidence=json.loads(path.read_text(encoding='utf-8'))
        if not evidence.get('passed') or not evidence.get('source_unchanged'):raise ValueError('Dispatch evidence failed')
        for name,sha in evidence['source_hashes'].items():
            if name.startswith('src/') and hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha:raise ValueError('Source differs from evidence')
        for row in evidence['rows']:observations.setdefault((row['method'],row['line']),[]).append(row)
    lines=['# UI 컨트롤 정적 연결 목록','',
           '소스의 button/toggle/choices/form 호출 지점을 모두 열거한다. 반복 생성되는 항목은 하나의 호출 지점으로 표시한다. '+
           '**실제 클릭·Controller·DB/API 성공을 전수 검증했다는 뜻이 아니다.** 기능별 확인과 미검증은 [UI 기능 감사](UI-FUNCTIONAL-AUDIT.md)를 따른다.', '',
           f'정적 호출 지점 {len(rows)}개. Tk Entry 입력란과 SelectionList의 각 데이터 행은 포함하지 않는다. 동적 항목·중첩 콜백은 소스를 확인해야 한다.', '',
           '|소스 위치|종류|표시 또는 분류|확인된 메서드 참조|실행 검증|','|---|---|---|---|---|']
    for row in rows:
        label=row['label'].replace('|',' / ').replace('\n',' ')
        ref=', '.join(row['callbacks']) or '중첩 함수/Controller · 소스 참조'
        observed=observations.get((row['method'],row['line']),[]) if row['kind'] in ('button','toggle') else []
        scope=('클릭→Controller 확인 · 일부 경계 mock' if any(r['commands'] for r in observed) else '화면/팝업·취소 확인') if observed else '개별 실행 증거 미부여'
        if args.evidence:scope+=' · [성공/실패/저장 범위](UI-ACTION-QA.md)'
        lines.append(f"|[{row['method']}:{row['line']}](../{row['file']}#L{row['line']})|{row['kind']}|{label}|{ref}|{scope}|")
    output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Static control call sites: {len(rows)}; not execution coverage')


if __name__=='__main__':main()
