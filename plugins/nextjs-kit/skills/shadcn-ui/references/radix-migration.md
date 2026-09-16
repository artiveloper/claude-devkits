# Radix → Base UI 이관 가이드

> `shadcn-ui` 스킬의 참조 문서. 기존 Radix 기반 코드를 Base UI로 옮길 때만 읽는다. 신규 코드는 처음부터 Base UI로 작성하므로 읽을 필요 없다.
> 아래 명령은 `npx` 기준이다 — 프로젝트가 쓰는 패키지 매니저(`pnpm dlx`/`bunx`)로 바꿔 실행한다.

### Radix → Base UI 대응표

| 영역 | Radix (레거시) | Base UI (기준) |
|------|---------------|----------------|
| 패키지 | `@radix-ui/react-*` 개별 설치 | `@base-ui/react` 단일 + 서브패스 import |
| 합성 | `asChild` + `Slot` | `render` prop |
| 합성 유틸 | `Slot` | `useRender` (`@base-ui/react/use-render`) |
| 팝업 내용 | `*.Content` | `*.Positioner` + `*.Popup` |
| 위치 prop | `Content`의 `side`/`align` | `Positioner`의 `side`/`align`/`sideOffset` |
| 열림 상태 | `data-state="open"` | `data-open` / `data-closed` |
| 애니메이션 | `data-[state=open]:animate-in` | `transition` + `data-starting-style` / `data-ending-style` |
| 그룹 헤딩 라벨 | 팝업 내 자유 배치 | 헤딩을 둘 때는 `Group` 내부에 중첩 |
| 위치 계산 커스텀 | Radix 내부 로직 | Floating UI(`@floating-ui/react`) 직접 사용 |

이 표는 **`@base-ui/react`를 직접 쓰는 코드**에 적용된다. shadcn이 생성한 `@/components/ui/*` 래퍼는
이관 후에도 평면 이름(`Dialog`/`DialogTrigger`/`DialogContent`…)을 유지하므로, 소비하는 쪽 코드는 대부분 그대로다.

### 이관 절차 — 스킬 기반 점진 이관

공식 경로는 코드모드 일괄 변환이 아니라 **컴포넌트 단위 점진 이관**이다.

1. Radix는 deprecated가 아니다 — 한 번에 갈아엎지 않는다. 혼재 상태는 허용하되, 신규 코드는 항상 Base UI.
2. `npx skills add shadcn/ui`로 shadcn 공식 스킬을 설치한 뒤, 스킬에 "<컴포넌트>를 Base UI로 이관해줘"처럼 **자연어로 지시**해 컴포넌트별로 진행한다(CLI 명령이 아니다).
3. 각 컴포넌트마다 `.migration/<component>.md` 리포트가 남는다 — 동작 차이를 여기서 확인한다.
4. **컴포넌트당 1커밋**으로 브랜치를 쌓는다. 문제가 생기면 브랜치를 지우는 것이 롤백이다.
5. CLI에도 `npx shadcn@latest migrate radix` 서브타입이 있다(`--from` / `--to` / `--list`). 다른 서브타입은 `cn`, `icons`, `base-color`, `rtl`.

### 이관 후 확인 항목

- `asChild` 잔존 여부 — 남아 있으면 조용히 무시된다.
- `data-[state=...]` 셀렉터 잔존 여부 — Base UI는 `data-open`/`data-closed`를 쓴다.
- `side`/`align`이 `Positioner`로 옮겨졌는지.
- `render`로 넘긴 커스텀 컴포넌트의 ref forward + props spread.
- **`<Button asChild><Link/></Button>`을 `<Button render={<Link/>}>`로 기계적으로 바꾼 곳** — 링크에는
  이 패턴을 쓰지 않는다(Base UI Button이 `role="button"`을 강제한다). `buttonVariants()` + 평범한 `<Link>`로 되돌린다.
