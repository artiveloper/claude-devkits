# claude-devkits — 개발 스택별 에이전트·스킬 마켓플레이스

여러 프로젝트가 공통으로 재사용하는 **아키텍처/품질 리뷰 지식**을 에이전트·스킬로 모아둔 **Claude Code 플러그인 마켓플레이스**입니다.

이 저장소가 단일 소스입니다. 여기에 커밋하면 설치된 모든 프로젝트에 자동으로 반영되며, **프로젝트 쪽 파일은 건드릴 일이 없습니다.**

각 에이전트는 독립적으로 호출되는 것을 전제로 작성됐습니다(에이전트 간 통신 없음).

## 설치

```bash
claude plugin marketplace add artiveloper/claude-devkits

# 필요한 킷만 설치 (기본 스코프: user → 모든 프로젝트에서 사용 가능)
# 원칙 킷 — 스택 불문, 계층별
claude plugin install common-kit@claude-devkits      # 시스템 아키텍처 (모든 프로젝트)
claude plugin install backend-kit@claude-devkits     # 백엔드·DB·QA 원칙
claude plugin install frontend-kit@claude-devkits    # 프론트엔드·디자인 시스템·QA 원칙

# 기술 킷 — 해당 스택을 쓰는 프로젝트만
claude plugin install python-kit@claude-devkits      # Python 클린코드
claude plugin install nextjs-kit@claude-devkits      # Next.js·React Query·shadcn/Base UI
claude plugin install supabase-kit@claude-devkits    # Supabase 인증·RLS·키 관리

# 도구 킷 — 프로젝트 문서 스캐폴드 (스택 불문)
claude plugin install project-docs-kit@claude-devkits # /init-project-docs 명령어
```

user 스코프로 설치하면 **프로젝트마다 설정 파일을 둘 필요가 없습니다.** 특정 프로젝트에만 적용하려면 `--scope project`(팀 공유용 `.claude/settings.json`에 기록)를 씁니다.

팀 단위로 자동 설치시키려면 프로젝트의 `.claude/settings.json`에 선언만 커밋하면 됩니다.

```json
{
  "extraKnownMarketplaces": {
    "claude-devkits": { "source": { "source": "github", "repo": "artiveloper/claude-devkits" } }
  },
  "enabledPlugins": { "backend-kit@claude-devkits": true }
}
```

### 업데이트

플러그인·마켓플레이스 항목 어디에도 `version`을 두지 않았습니다. 따라서 **버전은 커밋 SHA로 해석되고, 이 저장소에 push하면 그대로 최신 내용이 전파됩니다.** (`claude plugin validate`가 version 미지정 경고를 내지만 의도된 것입니다 — version을 박으면 그 값을 올려야만 업데이트가 나갑니다.)

마켓플레이스는 기본적으로 하루 1회 자동 갱신됩니다(`pluginAutoUpdateSettings.checkFrequencyMinutes`, 기본 1440). 즉시 반영하려면:

```
/plugin marketplace update claude-devkits
/reload-plugins
```

## 설계 철학

- **원칙 스킬은 스택 무관하게** 담는다. 언어·프레임워크에 종속된 규칙(예: Next.js App Router, Supabase 인증)은 원칙 스킬에 섞지 않고 별도 **기술 스킬**로 분리한다.
- **에이전트는 얇게, 원칙은 스킬에** 둔다. 에이전트는 역할·판단 태도만 정의하고, 실제 판단 기준은 짝이 되는 스킬에서 로드한다.
- **오케스트레이션은 프로젝트 몫이다.** 여러 에이전트를 순서대로 엮는 것과 프로젝트 특이사항은 각 프로젝트에서 구성한다. 이 저장소의 원본은 항상 범용성을 유지한다.
- **원칙 킷과 기술 킷을 분리한다.** 원칙 킷(`common`/`backend`/`frontend`)은 스택 불문 판단 기준만 담아 어떤 프로젝트든 설치할 수 있게 하고, 특정 언어·프레임워크·벤더에 묶인 스킬(`python-kit`/`nextjs-kit`/`supabase-kit`)은 독립 기술 킷으로 뺀다 — 그 스택을 쓰는 프로젝트만 설치한다. Node 백엔드에 Python 가이드가, Vue 프론트에 Next.js 가이드가 딸려오지 않는다.
- **에이전트·스킬 본문에 배포 방법을 적지 않는다.** "이 파일을 복사해서 쓰라" 같은 안내는 플러그인 모델과 모순되고, 에이전트가 호출될 때마다 컨텍스트를 차지한다. 배포·확장 방법은 이 README에만 둔다.

## 저장소 구조

```
.claude-plugin/marketplace.json     ← 마켓플레이스 카탈로그
plugins/
├─ common-kit/
│  ├─ .claude-plugin/plugin.json
│  ├─ agents/   system-architect.md
│  └─ skills/   system-architecture/
├─ backend-kit/                       ← 원칙 (스택 불문)
│  ├─ .claude-plugin/plugin.json
│  ├─ agents/   backend-architect.md, dba-advisor.md, qa-backend.md
│  └─ skills/   backend-architecture/, db-architecture/, qa-backend-strategy/
├─ frontend-kit/                      ← 원칙 (프레임워크 불문)
│  ├─ .claude-plugin/plugin.json
│  ├─ agents/   design-reviewer.md, frontend-architect.md, qa-frontend.md
│  └─ skills/   design-system/, frontend-architecture/, qa-frontend-strategy/
├─ python-kit/                        ← 기술 (Python)
│  └─ skills/   python-guide/
├─ nextjs-kit/                        ← 기술 (Next.js/React 스택)
│  └─ skills/   nextjs-guide/, react-query-guide/, shadcn-ui/
├─ supabase-kit/                      ← 기술 (Supabase)
│  └─ skills/   supabase-guide/
└─ project-docs-kit/                  ← 도구 (문서 스캐폴드, 스택 불문)
   ├─ commands/    init-project-docs.md
   └─ templates/   project-docs/ (README·docs/product·status·runbook·onboarding·decisions)
```

> `agents/`·`skills/`는 반드시 **플러그인 루트**에 둡니다. `.claude-plugin/` 안에는 `plugin.json`만 들어갑니다 — 가장 흔한 실수입니다.

각 킷에는 추가로 두 가지가 있습니다:
- `evals/` — 스킬 **발동/비발동 회귀 테스트** (`claude plugin eval` 형식, early access). 케이스마다 실제 사용자 프롬프트와 grader가 있다.
- 긴 기술 스킬의 `references/` — 조건부 상세(마이그레이션 절차 등)를 분리해, 트리거 후 로드 비용을 줄인다. 예: `supabase-guide/references/key-migration.md`, `supabase-guide/references/rls-testing.md`, `nextjs-guide/references/nextjs-16-baseline.md`, `shadcn-ui/references/radix-migration.md`

### 상시 토큰 비용

설치한 킷의 스킬·에이전트 **설명(description)** 만 항상 로드되고, 본문은 실제로 발동할 때 로드됩니다.

| 킷 | 성격 | 상시 | 구성 |
|----|------|------|------|
| `common-kit` | 원칙 | ~280 tok | 에이전트 1 + 스킬 1 |
| `backend-kit` | 원칙 | ~690 tok | 에이전트 3 + 스킬 3 |
| `frontend-kit` | 원칙 | ~655 tok | 에이전트 3 + 스킬 3 |
| `python-kit` | 기술 | ~240 tok | 스킬 1 |
| `nextjs-kit` | 기술 | ~760 tok | 스킬 3 |
| `supabase-kit` | 기술 | ~275 tok | 스킬 1 |
| `project-docs-kit` | 도구 | ~0 tok | 명령어 1 (슬래시 호출 시에만 로드) |

*0.2.0에서 description에 "다루지 않는 것" 경계를 추가해 원칙 킷 수치가 소폭 늘었다 — 스킬 간 트리거 충돌을 줄이기 위한 의도적 비용이다.*

`claude plugin details <이름>` 으로 언제든 확인할 수 있습니다.

## 에이전트 ↔ 원칙 스킬

### `common-kit` — 횡단(시스템) 설계

| 에이전트 | 스킬 | 담당 |
|----------|------|------|
| `system-architect` | `system-architecture` | 요구사항(FR/NFR) 구조화, 규모별 기술 스택 선정 규율, KISS·확장 지점, 도메인 간 경계 조율 |

### `backend-kit` — 백엔드

| 에이전트 | 스킬 | 담당 |
|----------|------|------|
| `backend-architect` | `backend-architecture` | 계층 분리, API 계약·응답 봉투, 입력 검증, 트랜잭션 경계, 인증/인가, 보안 기본, 에러 처리 |
| `dba-advisor` | `db-architecture` | 정규화, 인덱스 전략, 마이그레이션 안전성, N+1/락 이슈 |
| `qa-backend` | `qa-backend-strategy` | API 계약 검증, 통합 테스트 우선순위, 동시성·회귀 방지 |

### `frontend-kit` — 프론트엔드

| 에이전트 | 스킬 | 담당 |
|----------|------|------|
| `frontend-architect` | `frontend-architecture` | 상태 분류, 컴포넌트 경계, 데이터 fetching, 낙관적 업데이트 롤백, 에러 경계, 폼 검증 이중화 |
| `qa-frontend` | `qa-frontend-strategy` | 행동 기반 컴포넌트 테스트, E2E 우선순위, 안정적 셀렉터 |
| `design-reviewer` | `design-system` | 디자인 토큰, 컴포넌트 재사용, 반응형/모바일 퍼스트, 접근성, 로딩·빈·에러 상태 |

각 원칙 스킬 하단에는 `## 리뷰 시 체크 우선순위`가 있어, 리뷰 결과가 호출마다 흔들리지 않도록 판단 순서를 고정한다.

## 기술 스킬

원칙 스킬과 달리 특정 언어·프레임워크에 종속된 실무 규칙을 담는다. 에이전트에 고정으로 묶이지 않고, 해당 기술을 다룰 때 스킬 설명(description) 매칭으로 로드되도록 작성됐다.

| 스킬 | 킷 | 범위 |
|------|----|------|
| `python-guide` | `python-kit` | 범용 Python 클린코드 — src layout, 타입 힌트(mypy/pyright), uv/poetry·pyproject.toml, ruff, pytest, 예외 계층, asyncio |
| `supabase-guide` | `supabase-kit` | Supabase SSR 인증(`@supabase/ssr`, getClaims/getUser), grant + RLS 2층 권한 모델·정책 성능, pgTAP RLS 테스트, 타입 생성, 마이그레이션·선언적 스키마, 신규 publishable/secret 키. 인증·토큰 갱신 예시는 Next.js App Router 기준 |
| `nextjs-guide` | `nextjs-kit` | App Router 메커니즘 — 파일 컨벤션, Server/Client 경계와 합성, `loading.tsx`+Suspense 스트리밍, 서버 데이터 보안(DAL/DTO·Server Action 재인가), 캐시·에러 처리, `proxy.ts`와 matcher. **Next.js 16 기준** |
| `react-query-guide` | `nextjs-kit` | 데이터 레이어 — query keys/options/prefetch, mutation·invalidate·낙관적 업데이트, Server Actions, 실시간 구독, 상태 소유권. 백엔드 무관(데이터 접근 모듈은 자리표시자) |
| `shadcn-ui` | `nextjs-kit` | Tailwind/shadcn UI 구현 패턴. 프리미티브는 **Base UI(`@base-ui/react`)** 기준 — 합성(render prop), `data-*` 상태 스타일링, Sidebar 레이아웃 |

> 기술 스킬도 **특정 프로젝트에 종속되지 않는다.** 코드 예시는 중립적인 경로(`src/...`, `@/components/ui/*`)와 예시 도메인(`resources`, `catalog_items` 등)을 쓰므로, 프로젝트에 적용할 때 자기 경로·테이블명으로 바꿔 읽으면 된다.

## 프로젝트 특이사항은 어떻게 하나

원본을 고쳐 쓰지 말고, **프로젝트의 `.claude/`에 얇은 보완 파일만** 둡니다. 그래야 이 저장소의 갱신분이 계속 자동으로 따라옵니다.

- 프로젝트 고유 규칙 → 해당 프로젝트 `CLAUDE.md` 또는 `.claude/skills/<프로젝트-규칙>/SKILL.md`
- 여러 에이전트를 묶는 오케스트레이션 → 그 프로젝트의 하네스에서 구성

## 스킬·에이전트 추가하기

1. 해당 킷의 `plugins/<킷>/skills/<이름>/SKILL.md` (또는 `agents/<이름>.md`)를 추가한다.
   - description은 **[무엇을] + [언제 사용] + [무엇은 다루지 않는지(경계)]** 3요소로 쓴다. 상세 작성 규칙은 `docs/agent-skill-best-practices.md` 참조.
   - 운영하며 발견한 함정은 해당 스킬의 **Gotchas 섹션**에 축적한다.
2. `claude plugin validate ./plugins/<킷>` 으로 검증한다.
3. `evals/`에 발동/비발동 케이스를 추가하고, 로컬에서 동작을 확인한다.
   ```bash
   claude --plugin-dir ./plugins/<킷>
   claude plugin eval ./plugins/<킷>   # early access 활성화 시
   ```
4. `plugin.json`의 `version`을 올리고 커밋 & push → 설치된 모든 프로젝트에 전파. (version을 안 올리면 업데이트가 전파되지 않는다)
