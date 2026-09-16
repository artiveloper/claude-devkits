# shadcn 설정·CLI·토큰 레퍼런스

> `shadcn-ui` 스킬의 참조 문서. 프로젝트를 처음 세팅하거나, `components.json`을 손보거나,
> 디자인 토큰·Button variant를 추가하거나, CLI 명령의 정확한 플래그가 필요할 때만 읽는다.
> 일상적인 컴포넌트 작성 규칙은 SKILL.md에 있다.

## 목차
1. [CLI 명령과 플래그](#cli-명령과-플래그)
2. [components.json 필드](#componentsjson-필드)
3. [`cn` 유틸 — 독립 패키지로 이동](#cn-유틸--독립-패키지로-이동)
4. [디자인 토큰 전체 목록](#디자인-토큰-전체-목록)
5. [Base UI 전역 설정](#base-ui-전역-설정)
6. [Button variant / size 목록](#button-variant--size-목록)

아래 명령은 `npx` 기준이다 — 프로젝트가 쓰는 패키지 매니저(`pnpm dlx`/`bunx`/`yarn dlx`)로 바꿔 실행한다.

## CLI 명령과 플래그

| 명령 | 용도 |
|------|------|
| `npx shadcn@latest init` | 프로젝트 초기화 (`components.json` 생성, 토큰 주입) |
| `npx shadcn@latest add <component>` | 컴포넌트 소스를 프로젝트에 복사 |
| `npx shadcn@latest docs <component>` | 컴포넌트 문서·코드·예제를 CLI에서 조회 |
| `npx shadcn@latest info` | 감지된 프레임워크·설정·설치된 컴포넌트 확인 |
| `npx shadcn@latest migrate <type>` | 마이그레이션 실행 (`cn`, `icons`, `base-color`, `rtl`, `radix`) |
| `npx shadcn@latest mcp init --client claude` | shadcn MCP 서버 등록 (레지스트리 브라우즈·검색·설치) |

주요 플래그:

- `-b, --base <base>` — 프리미티브 베이스 선택. 값은 `base`(Base UI) · `radix` · `aria`(React Aria).
  기본값은 프로젝트에 설정된 base이고, 신규 프로젝트는 `base`다. **`radix`는 레거시 유지 목적 외 사용하지 않는다.**
- `--dry-run` / `--diff` / `--view` — `add` 실행 전에 무엇이 들어오는지 확인한다.
  기존 파일을 커스터마이징한 프로젝트에서는 덮어쓰기 전에 반드시 확인한다.
- `--json` — `docs` 결과를 구조화해 받는다.

컴포넌트 API가 확실하지 않으면 추측하지 말고 `docs`나 MCP로 실제 소스를 확인한다.
shadcn 공식 스킬(`npx skills add shadcn/ui`)을 설치하면 프로젝트 컨텍스트 감지·CLI·테마·레지스트리 절차가 함께 들어온다.

## components.json 필드

| 필드 | 값 / 비고 |
|------|----------|
| `style` | `new-york`만 유효 (`default`는 deprecated) |
| `tailwind.config` | Tailwind v4에서는 빈 문자열 |
| `tailwind.css` | 전역 CSS 파일 경로 (토큰이 주입되는 곳) |
| `tailwind.baseColor` | `neutral` · `stone` · `zinc` · `mauve` · `olive` · `mist` · `taupe` |
| `tailwind.cssVariables` | `true`면 CSS 변수 기반 테마, `false`면 유틸리티 클래스 직접 사용 |
| `tailwind.prefix` | Tailwind 클래스 접두사 (기존 CSS와 충돌할 때만) |
| `rsc` | React Server Components 사용 여부 — `true`면 `'use client'` 자동 삽입 |
| `tsx` | TypeScript 여부 |
| `aliases` | `components` · `ui` · `lib` · `hooks` · `utils` 경로 별칭 |
| `registries` | 멀티 레지스트리 정의 (사설 레지스트리는 인증 헤더 지정 가능) |

`baseColor`는 init 이후 바꾸려면 `npx shadcn@latest migrate base-color`를 쓴다 — 손으로 토큰을 다시 쓰지 않는다.

## `cn` 유틸 — 독립 패키지로 이동

`clsx` + `tailwind-merge` 보일러플레이트는 독립 패키지 `cn`으로 옮겨졌다. 새 `lib/utils.ts`는 한 줄이다.

```ts
// src/lib/utils.ts
export { cn } from "cn";
```

- 호출부 API는 그대로다(드롭인 교체). `cn("px-2", isActive && "bg-accent")` 사용법은 변하지 않는다.
- 기존 프로젝트 전환: `npx shadcn@latest migrate cn`.
- 기존 `lib/utils.ts`(clsx+twMerge 구현)도 계속 동작한다 — 전환은 선택이다. 다만 **새로 만들 때 옛 보일러플레이트를 손으로 복사해 넣지 않는다.**

## 디자인 토큰 전체 목록

`init`이 전역 CSS에 주입하는 기본 토큰(각각 `--x` / `--x-foreground` 쌍 형태):

`background` · `foreground` · `card` · `popover` · `primary` · `secondary` · `muted` · `accent` · `destructive` ·
`border` · `input` · `ring` · `chart-1`~`chart-5` ·
`sidebar` · `sidebar-foreground` · `sidebar-primary` · `sidebar-accent` · `sidebar-border` · `sidebar-ring`

**`success`/`warning`은 기본 토큰이 아니다.** 필요하면 직접 추가한다 — `:root`/`.dark`에 oklch 값을 정의하고 `@theme inline`으로 Tailwind 유틸에 노출한다.

```css
:root {
  --warning: oklch(0.84 0.16 84);
  --warning-foreground: oklch(0.28 0.07 46);
}
.dark {
  --warning: oklch(0.48 0.13 84);
  --warning-foreground: oklch(0.96 0.02 84);
}
@theme inline {
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
}
```

이렇게 해야 `bg-warning text-warning-foreground`가 동작한다. 토큰을 추가한 뒤에는 해당 컴포넌트의
`cva` variant 목록(예 Badge의 `variant`)에도 항목을 추가해야 `variant="warning"`을 쓸 수 있다.
라이트/다크 양쪽 값을 같이 정의하지 않으면 한쪽 테마에서 대비가 깨진다.

## Base UI 전역 설정

shadcn이 Base UI 프리미티브를 쓰므로 전역 CSS에 두 가지를 넣어 둔다.

```css
:root {
  isolation: isolate;   /* 팝업이 z-index 충돌 없이 뜨도록 별도 stacking context 생성 */
}
body {
  position: relative;   /* iOS 26+ Safari에서 스크롤 시 Backdrop이 깨지는 문제 대응 */
}
```

## Button variant / size 목록

- `variant`: `default` · `outline` · `ghost` · `destructive` · `secondary` · `link`
- `size`: `default` · `xs` · `sm` · `lg` · `icon` · `icon-xs` · `icon-sm` · `icon-lg`

`xs`/`sm`/`icon-xs`/`icon-sm`은 터치 타겟 44px에 못 미친다 — 포인터 입력이 전제인 데스크탑 밀집 UI에만 쓰고,
모바일에서 눌리는 버튼에는 `default` 이상 또는 `min-h-11`을 준다.
`variant`를 추가하려면 컴포넌트 파일의 `cva` 정의에 항목을 넣고, 색은 위 디자인 토큰으로 참조한다.
