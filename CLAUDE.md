# claude-devkits 작업 규칙

개발 스택별 에이전트·스킬·커맨드 플러그인 마켓플레이스. 여기 커밋하면 설치된 모든 프로젝트에 전파된다.
규칙의 근거·상세는 `docs/agent-skill-best-practices.md` 참조 (이 파일은 실무 체크리스트만).

## 스킬(SKILL.md) 수정 시

- **description 3요소**: [무엇을] + [언제 사용 — 사용자가 실제 입력할 키워드 포함] + [무엇은 다루지 않는지 — 겹칠 수 있는 스킬명 명시]. 1,024자 이내.
- **YAML 함정**: 한 줄 description에 `: `(콜론+공백)를 넣지 않는다 — "예: X"는 "X 등"으로 바꾼다. 여러 줄이면 `description: >` 블록 스칼라 사용.
- **본문 500줄 미만**. 넘을 조짐이면 조건부 상세(마이그레이션 절차 등)를 `references/`로 분리 — 참조는 SKILL.md에서 1단계 깊이만, 100줄 넘는 참조 파일엔 목차.
- **킷 성격 준수**: 원칙 킷(common/backend/frontend)에는 스택 불문 판단 기준만, 기술 킷(python/nextjs/supabase)에는 해당 스택 종속 내용만. LLM이 이미 아는 일반 지식은 넣지 않는다.
- **킷 경계 가드**: 다른 킷의 스킬을 참조할 때는 반드시 "미설치 시 건너뛴다" 가드를 붙인다. 같은 킷 내 참조는 가드 불필요.
- **Gotchas**: 운영하며 발견한 함정은 새 섹션을 만들지 말고 해당 스킬의 기존 Gotchas 섹션에 추가한다.
- 용어는 한 문서에서 하나로 통일, 시한성 표현("2026년부터는…") 금지, 선택지는 기본값 하나 + 예외 경로만.

## 에이전트(agents/*.md) 수정 시

- **단일 책임 유지**. 역할이 늘어나면 에이전트를 쪼갠다.
- description = 호출 조건 + 타 에이전트와의 소관 경계. 상세 지침은 본문에.
- `tools`는 최소로 (자문·리뷰형은 `Read, Grep, Glob` 유지). `skills:` 프리로드는 **같은 킷 스킬만** 가능.
- 타 킷 에이전트를 언급할 때는 "(해당 킷 설치 시)"를 붙인다.
- 이름은 전역 충돌을 피해 구체적으로 (`architect` ❌ → `system-architect` ✅).

## 커맨드(commands/*.md) 수정 시

- **명시 호출 아티팩트**다. 슬래시로 사용자가 직접 부르므로 자연어 트리거·description 3요소·evals 대상이 아니다. description은 "무엇을 하는가" 한 줄이면 된다.
- 파일명이 명령어 이름이다(`init-project-docs.md` → `/init-project-docs`). **전역 충돌을 피해 구체적으로** 짓는다 — 빌트인(`/init` 등)이나 흔한 이름을 피한다.
- frontmatter는 `description`·`argument-hint`·`allowed-tools`만 쓰고 `allowed-tools`는 최소로 둔다. 인자는 본문에서 `$ARGUMENTS`로 받는다.
- 번들 리소스(템플릿 등)는 킷 루트 하위(`templates/` 등)에 두고 본문에서 `${CLAUDE_PLUGIN_ROOT}/...`로 참조한다 — 절대경로·상대경로 금지.
- **파괴적 동작 금지**: 사용자 파일을 덮어쓰지 않는다. 기존 파일은 건너뛰고 결과(설치됨/건너뜀)를 보고하도록 프롬프트에 명시한다.
- 상시 토큰 비용이 없다(호출 시에만 로드). 문서 스캐폴드처럼 스택 불문 도구는 원칙/기술 킷에 섞지 말고 전용 "도구" 킷으로 분리한다.

## 커밋 전 체크

1. `claude plugin validate ./plugins/<킷>` 통과 (마켓플레이스 전체는 `claude plugin validate .`)
2. frontmatter YAML 파싱 확인 (validate가 관대하게 통과시키는 케이스가 있다)
3. 스킬 추가/트리거 변경 시 `evals/`에 발동·비발동 케이스 추가 또는 갱신
4. **`plugin.json`의 `version` bump** — 안 올리면 설치처에 업데이트가 전파되지 않는다
5. description 합산이 커지는 변경이면 예산 확인 (전 킷 합산 ~4,000자 수준 유지, 목록 예산 ~15,000자)

## 하지 말 것

- `agents/`·`skills/`·`commands/`를 `.claude-plugin/` 안에 두기 (플러그인 루트에 둔다)
- 커맨드에서 사용자 파일을 덮어쓰거나, 번들 리소스를 `${CLAUDE_PLUGIN_ROOT}` 없이 절대·상대경로로 참조하기
- 스킬 하나에 여러 킷의 관심사 섞기 (God Skill) — 경계가 모호하면 분리
- 프로젝트 종속 내용(특정 서비스명·경로) 넣기 — 예시는 자리표시자(`resources` 등)로

## 하네스: 킷 품질 개선

**목표:** plugins/ 아래 스킬·에이전트를 베스트 프랙티스에 맞게 유지·개선한다.

**트리거:** 킷/스킬/에이전트/커맨드의 수정·추가·감사·릴리스 요청 시 `kit-improve` 스킬을 사용하라. 규칙·파일 위치 등 단순 질문은 직접 응답 가능.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-09-10 | 초기 구성 (kit-editor·kit-auditor + kit-improve·kit-authoring·kit-audit) | 전체 | - |
| 2026-09-11 | 커맨드 아티팩트 규칙 추가 + project-docs-kit(/init-project-docs) 신설 | project-docs-kit | 프로젝트 초기 문서 스타터를 슬래시 명령어로 설치 |
| 2026-09-16 | supabase-guide 개정 (getClaims 권장, grant+RLS 2층 모델, pgTAP 테스트, 선언적 스키마) + references 3종 | supabase-kit | Supabase 공식 문서·agent-skills 베스트 프랙티스 반영 |

