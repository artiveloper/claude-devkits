#!/usr/bin/env python3
"""claude-devkits 구조 감사 스크립트.

기계적으로 검증 가능한 규칙만 검사한다. 판단형 검사(트리거 near-miss,
God Skill, 킷 성격 위반)는 kit-audit 스킬의 수동 체크리스트로 수행한다.

사용: python3 .claude/skills/kit-audit/scripts/audit.py [저장소 루트]
종료 코드: 0=통과(WARN 허용), 1=FAIL 존재
"""
import json, re, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FAIL pyyaml 필요: pip install pyyaml"); sys.exit(1)

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
issues = []  # (level, path, msg)

def add(level, path, msg): issues.append((level, str(path), msg))

def frontmatter(p):
    parts = p.read_text(encoding="utf-8").split("---")
    if len(parts) < 3: return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        add("FAIL", p, f"frontmatter YAML 파싱 실패: {str(e).splitlines()[0]}")
        return None

skills = sorted(ROOT.glob("plugins/*/skills/*/SKILL.md"))
agents = sorted(ROOT.glob("plugins/*/agents/*.md"))
plugin_of = lambda p: p.relative_to(ROOT / "plugins").parts[0]
skill_names = {p.parent.name: plugin_of(p) for p in skills}
GUARDS = ["미설치", "설치돼 있", "설치 시", "설치된 경우", "설치되지 않"]

total_desc = 0
for p in skills + agents:
    fm = frontmatter(p)
    if fm is None: continue
    desc = str(fm.get("description", "") or "")
    body_fm = p.read_text(encoding="utf-8").split("---")[1]
    # description 존재·길이
    if not desc.strip(): add("FAIL", p, "description 비어 있음")
    if len(desc) > 1024: add("FAIL", p, f"description {len(desc)}자 — 1,024자 초과")
    total_desc += len(desc)
    # 한 줄 description의 콜론+공백 (블록 스칼라 '>'는 제외)
    m = re.search(r"^description:[ \t]*(?!>)(\S.*)$", body_fm, re.M)
    if m and ": " in m.group(1): add("FAIL", p, "한 줄 description에 ': ' 포함 — YAML 플레인 스칼라 위반")
    # 경계(3요소) 휴리스틱
    if not any(k in desc for k in ["다루지 않", "소관", "Not for"]):
        add("WARN", p, "description에 '다루지 않는 것' 경계가 없음")

for p in skills:
    text = p.read_text(encoding="utf-8")
    lines = text.count("\n") + 1
    if lines >= 500: add("FAIL", p, f"본문 {lines}줄 — 500줄 초과, references/ 분리 필요")
    elif lines >= 400: add("WARN", p, f"본문 {lines}줄 — 500줄 근접, 분리 검토")
    # 킷 경계 가드: 타 킷 스킬 백틱 참조 존재 시 파일 어딘가에 가드 문구 필요
    my_kit = plugin_of(p)
    xrefs = {n for n in re.findall(r"`([a-z0-9-]+)`", text)
             if n in skill_names and skill_names[n] != my_kit and n != p.parent.name}
    if xrefs and not any(g in text for g in GUARDS):
        add("FAIL", p, f"타 킷 스킬 참조 {sorted(xrefs)} 존재하나 미설치 가드 문구 없음")
    # references/ 1단계 + 100줄 목차
    for ref in (p.parent / "references").glob("*.md"):
        rl = ref.read_text(encoding="utf-8").count("\n") + 1
        if rl > 100 and "목차" not in ref.read_text(encoding="utf-8")[:800] and "## " not in ref.read_text(encoding="utf-8")[:400]:
            add("WARN", ref, f"참조 파일 {rl}줄인데 상단 목차 없음")

for p in agents:
    fm = frontmatter(p)
    if fm is None: continue
    if "tools" not in fm: add("WARN", p, "tools 미지정 — 전체 도구 허용됨. 자문형이면 'Read, Grep, Glob' 권장")
    for s in fm.get("skills") or []:
        if s not in skill_names: add("FAIL", p, f"skills: 프리로드 대상 '{s}' 스킬 없음")
        elif skill_names[s] != plugin_of(p): add("FAIL", p, f"skills: '{s}'는 타 킷({skill_names[s]}) — 같은 킷만 프리로드 가능")

for pj in sorted(ROOT.glob("plugins/*/.claude-plugin/plugin.json")):
    d = json.loads(pj.read_text(encoding="utf-8"))
    if "version" not in d: add("FAIL", pj, "version 필드 없음 — 업데이트가 전파되지 않음")

# eval 커버리지
for p in skills:
    kit = plugin_of(p); name = p.parent.name
    if not (ROOT / f"plugins/{kit}/evals/{name}-trigger").is_dir():
        add("WARN", p, f"evals/{name}-trigger 케이스 없음")
for kit_dir in sorted((ROOT / "plugins").iterdir()):
    if kit_dir.is_dir() and (kit_dir / "skills").is_dir() and not (kit_dir / "evals/no-trigger").is_dir():
        add("WARN", kit_dir, "evals/no-trigger(비발동) 케이스 없음")

# README 동기화 (에이전트명 언급 여부)
readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
for p in agents:
    fm = frontmatter(p) or {}
    if fm.get("name") and f"`{fm['name']}`" not in readme:
        add("WARN", p, f"README에 에이전트 `{fm['name']}` 언급 없음 — 표 동기화 확인")

if total_desc > 8000:
    add("WARN", "(전체)", f"description 합산 {total_desc}자 — 예산(~15,000자) 대비 여유 축소 중")

for level in ("FAIL", "WARN"):
    for l, path, msg in issues:
        if l == level: print(f"{l}  {path}  —  {msg}")
fails = sum(1 for l, _, _ in issues if l == "FAIL")
print(f"\n검사 대상: 스킬 {len(skills)} / 에이전트 {len(agents)} · description 합산 {total_desc}자")
print(f"결과: FAIL {fails} / WARN {sum(1 for l,_,_ in issues if l=='WARN')}")
sys.exit(1 if fails else 0)
