---
name: shadcn-ui
description: >
  Tailwind/shadcn UI 구현 패턴 가이드 — 프리미티브는 Base UI(@base-ui/react) 기준.
  모바일 퍼스트 className, Base UI 합성(render prop)·data-* 상태 스타일링, 디자인 토큰(CSS 변수)·data-slot 덮어쓰기,
  shadcn Sidebar 레이아웃, 액션 버튼·상태 Badge·날짜 포맷 중앙화·공유 스켈레톤, shadcn CLI 툴링.
  Tailwind, shadcn, Base UI, render prop, shadcn 디자인 토큰(CSS 변수), Sidebar, Skeleton, 반응형, UI 컴포넌트 작업 시 사용.
  App Router 메커니즘(nextjs-guide), 데이터 훅 정의(react-query-guide), 라이브러리 불문 원칙(design-system)은 다루지 않는다.
---

# shadcn/Tailwind — UI 구현 패턴

> Next.js App Router 메커니즘(Server/Client 경계·loading.tsx·route group) → `nextjs-guide` 스킬 참조
> 데이터 레이어(React Query·query keys/options·prefetch·mutation·실시간 구독) → `react-query-guide` 스킬 참조
> 라이브러리 불문 UI 원칙(모바일 퍼스트·터치 타겟·반응형·로딩/빈/에러 상태·상태 색상 일관성) → `design-system` 스킬 참조. 이 스킬은 그 원칙들의 **Tailwind/shadcn 구현**만 다룬다.
> **frontend-kit 미설치 시**: 이 문서에 나오는 `design-system` 참조는 전부 건너뛴다 — 없는 스킬을 찾거나 로드하려 하지 않는다.

**프리미티브 기준: Base UI(`@base-ui/react`).** shadcn/ui의 기본 프리미티브는 Base UI다. 신규 컴포넌트·신규 코드는 Radix가 아니라 Base UI로 작성한다(§1).

---

## 0. UI 1원칙: 모바일 퍼스트

> 모바일 퍼스트 원칙 자체(왜·판단 기준)는 `design-system` 스킬 참조. 이 섹션은 그 원칙의 **Tailwind/shadcn 구현**만 다루며, 아래 모든 섹션에 우선한다.

### Tailwind 사용 규칙

```tsx
// ✅ 모바일 기본, 데스크탑 확장
<div className="p-4 md:p-6">
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
<div className="text-sm md:text-base">

// ❌ 데스크탑 기준으로 먼저 설계
<div className="px-8 py-10">
<div className="grid grid-cols-4 gap-6">
```

### 레이아웃 — shadcn Sidebar

dashboard layout은 `SidebarProvider` + `SidebarInset` + `AppSidebar` 조합을 사용한다. 직접 `<aside>` 또는 고정 `w-60`을 사용하지 않는다.

```tsx
// app/(dashboard)/layout.tsx  ← layout.tsx 파일 컨벤션은 nextjs-guide
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/app-sidebar'

export default function DashboardLayout({ children }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />    {/* 모바일 햄버거 버튼 */}
        </header>
        <main className="flex-1 overflow-y-auto bg-muted/40 p-4 md:p-6">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
```

- 모바일: `SidebarTrigger` 클릭 시 Sheet 오버레이로 사이드바 열림 (`collapsible="offcanvas"`). 이 Sheet는 Base UI `Dialog` 위에 구현된 shadcn 컴포넌트다 — `@radix-ui/react-dialog`로 직접 대체 구현하지 않는다.
- 데스크탑: 사이드바가 고정 패널로 표시됨. `collapsible`은 `offcanvas`(기본) / `icon`(아이콘만 남김) / `none`(접기 없음) 중 하나다.
- 구성: `SidebarProvider` > `Sidebar`(`SidebarHeader` / `SidebarContent` > `SidebarGroup` > `SidebarGroupLabel`·`SidebarGroupAction`·`SidebarGroupContent` / `SidebarFooter` / `SidebarRail`) + `SidebarInset` + `SidebarTrigger`.
- `SidebarRail`을 넣으면 사이드바 가장자리를 드래그/클릭해 접을 수 있다. 키보드 단축키는 기본 `cmd/ctrl+B`(`SIDEBAR_KEYBOARD_SHORTCUT`).
- 폭은 `SIDEBAR_WIDTH` / `SIDEBAR_WIDTH_MOBILE` 상수로 정해진다. 한 화면에 사이드바가 둘 이상이면 각각 `--sidebar-width` / `--sidebar-width-mobile` 커스텀 속성을 style로 넘겨 개별 지정한다.

### 터치 타겟

터치 타겟 최소 44px 원칙(→ `design-system`)의 Tailwind 구현:

```tsx
// ✅ 충분한 터치 타겟
<Button className="min-h-11 px-4">액션</Button>

// ❌ 너무 작은 타겟
<button className="h-6 px-2">액션</button>
```

Button `size` 토큰 중 `xs`/`sm`/`icon-xs`/`icon-sm`은 44px에 못 미친다 — 포인터 입력이 전제인 데스크탑 밀집 UI(툴바·테이블 행 액션)에만 쓰고, 모바일에서 눌리는 버튼에는 `default` 이상이나 `min-h-11`을 준다. 전체 variant/size 목록 → `references/shadcn-setup.md`.

### 테이블 반응형

좁은 화면 테이블 처리(카드/수평 스크롤) 원칙(→ `design-system`)의 Tailwind 구현:

```tsx
// 수평 스크롤 (우선 처리)
<div className="overflow-x-auto">
  <table className="min-w-full">...</table>
</div>
```

### 금지 패턴

```tsx
// ❌ overflow-hidden으로 모바일 스크롤 차단
<div className="h-screen overflow-hidden">

// ❌ 고정 사이드바 너비 (항상 표시)
<aside className="w-60 flex-shrink-0">

// ❌ 고정 여백 (모바일에서 너무 좁음)
<div className="px-6 py-8">  // → p-4 md:p-6 사용
```

---

## 1. 프리미티브 레이어 — Base UI (`@base-ui/react`)

shadcn 컴포넌트(`@/components/ui/*`)의 내부 프리미티브는 **Base UI**다. 이 절은 Base UI 규약이 드러나는 지점을 모두 다룬다 — 원시 프리미티브를 직접 쓸 때(커스텀 팝업·합성)뿐 아니라, 래퍼를 통해 그대로 노출되는 prop과 상태 속성까지 포함한다.

### 두 레이어를 구분한다 — shadcn 래퍼 vs 원시 프리미티브

- **shadcn 래퍼**(`@/components/ui/dialog` 등)는 Base UI 전환 후에도 **평면 이름을 유지**한다: `Dialog` / `DialogTrigger` / `DialogContent` / `DialogHeader` / `DialogTitle`. 화면 코드는 이 래퍼를 쓰고, 이름은 Radix 시절과 같다.
- **구조 분리(`Positioner` + `Popup`)는 원시 프리미티브(`@base-ui/react/*`)를 직접 import할 때만** 드러난다. 래퍼는 그 두 겹을 `DialogContent` 같은 한 컴포넌트 안에 감춰 둔다.
- 반면 **`render` prop과 `data-*` 상태 속성은 래퍼·원시 양쪽에서 쓴다** — 래퍼가 받은 prop을 Base UI로 그대로 넘기기 때문이다. 그래서 `<Button render={<Link/>}>`도 문법적으로는 동작한다. 링크에 이 패턴을 쓰지 않는 이유는 "동작하지 않아서"가 아니라 Button이 `role="button"`을 강제하기 때문이다(→ 아래 금지 패턴).
- 따라서 "`Content`가 사라졌다"는 얘기는 원시 프리미티브 레이어의 얘기다 — 래퍼의 `DialogContent`를 찾아 고치려 들지 않는다. 래퍼 파일을 열어 내부를 바꿀 때는 원시 프리미티브 규칙이 적용된다.

### 패키지 & import

```bash
npm install @base-ui/react       # 단일 패키지 (Radix처럼 컴포넌트별 패키지를 추가하지 않는다)
                                 # pnpm/yarn/bun 등 프로젝트가 쓰는 패키지 매니저로 실행
```

```tsx
import { Dialog } from '@base-ui/react/dialog'      // 서브패스 import
import { Popover } from '@base-ui/react/popover'
```

- shadcn 컴포넌트 추가는 기본값 그대로: `npx shadcn@latest add <component>`(또는 `pnpm dlx`/`bunx`) → Base UI 버전이 설치된다.
- 베이스 선택 플래그는 `-b, --base <base>`이고 값은 `base`(Base UI) / `radix` / `aria`(React Aria)다. 신규 프로젝트 기본값은 `base`이며, **`radix`는 레거시 유지 목적 외 사용 금지**.
- 전역 CSS에 Base UI 요구 설정 두 줄을 넣어 둔다: 루트에 `isolation: isolate`(팝업 z-index 충돌 방지용 stacking context), `body { position: relative }`(iOS 26+ Safari에서 스크롤 시 Backdrop 깨짐 대응). 스니펫 → `references/shadcn-setup.md`.

### 합성 — `asChild` 대신 `render`

Base UI에는 `asChild`/`Slot`이 없다. 트리거를 다른 엘리먼트/커스텀 컴포넌트로 렌더링할 때는 `render` prop을 쓴다.

```tsx
// ✅ Base UI
<Menu.Trigger render={<Button variant="outline" />}>메뉴 열기</Menu.Trigger>
<Menu.Item render={<Link href="/resources" />}>목록으로</Menu.Item>

// ❌ Radix 시절 패턴 (Base UI에서 동작하지 않음)
<Menu.Trigger asChild><Button variant="outline">메뉴 열기</Button></Menu.Trigger>
```

- `render`에 넘기는 커스텀 컴포넌트는 **ref를 forward하고 받은 props를 DOM 노드에 모두 spread** 해야 한다. 안 하면 트리거 동작·접근성 속성이 사라진다.
- 상태에 따라 내용을 바꿔야 하면 함수 형태를 쓴다.

```tsx
<Switch.Thumb
  render={(props, state) => <span {...props}>{state.checked ? <CheckIcon /> : <XIcon />}</span>}
/>
```

- 앱 자체 컴포넌트에 "엘리먼트 교체" 기능이 필요하면 `Slot` 대신 `useRender`(`@base-ui/react/use-render`)로 구현한다.

### 구조 — `Content` 대신 `Positioner` + `Popup`

떠 있는 컴포넌트(Popover·Menu·Select·Tooltip)는 위치 계산 레이어(`Positioner`)와 내용 레이어(`Popup`)가 분리돼 있다. `side`/`align`/`sideOffset`은 **`Positioner`**에 준다.

```tsx
<Popover.Root>
  <Popover.Trigger render={<Button variant="outline" />}>필터</Popover.Trigger>
  <Popover.Portal>
    <Popover.Positioner side="bottom" align="start" sideOffset={8}>
      <Popover.Popup className="rounded-md border bg-popover p-4 shadow-md">
        <Popover.Title>필터</Popover.Title>
        <Popover.Description>조건을 선택하세요.</Popover.Description>
      </Popover.Popup>
    </Popover.Positioner>
  </Popover.Portal>
</Popover.Root>
```

- Dialog 계열 구성: `Root` / `Trigger` / `Portal` / `Backdrop` / `Viewport` / `Popup` / `Title` / `Description` / `Close`.
- 위치 계산을 직접 커스텀해야 하면 Radix 내부 로직 대신 Floating UI(`@floating-ui/react`)를 쓴다 — Base UI가 그 위에 서 있다.

### Select — `items` 매핑과 그룹 라벨

```tsx
const statusItems = [
  { value: null, label: '상태 전체' },        // 미선택 상태 = 플레이스홀더 겸 선택 해제 항목
  { value: 'active', label: '활성' },
  { value: 'inactive', label: '비활성' },
]

<Select items={statusItems}>
  <SelectTrigger className="w-full max-w-48"><SelectValue /></SelectTrigger>
  <SelectContent>
    <SelectGroup>
      <SelectLabel>상태</SelectLabel>
      {statusItems.map((item) => (
        <SelectItem key={String(item.value)} value={item.value}>{item.label}</SelectItem>
      ))}
    </SelectGroup>
  </SelectContent>
</Select>
```

- `items`를 `Select`에 넘기면 `SelectValue`가 값→라벨 매핑을 대신한다. 안 넘기면 선택된 raw value가 그대로 렌더된다.
- 미선택 상태는 위처럼 `value: null` 항목으로 표현한다 — 그 라벨이 플레이스홀더로 뜨고 팝업에서 선택 해제도 된다. (`<SelectValue placeholder="…" />`도 동작하지만 선택 해제는 따로 처리해야 한다.)
- **팝업에 섹션 헤딩을 두는 순간 `SelectGroup` 래핑이 필수**다 — `SelectLabel`은 부모 그룹과 자동으로 연관되므로 그룹 밖에 두면 연관이 생기지 않는다. 헤딩이 필요 없으면 `SelectContent` 아래 `SelectItem`만 나열해도 된다. Menu도 같다.
- 이름 혼동 주의: Base UI에는 **트리거**와 연관되는 폼 라벨 `Select.Label`과 팝업 내 그룹 헤딩 `Select.GroupLabel`이 따로 있다. shadcn이 export하는 `SelectLabel`은 후자다.

### 상태 스타일링 — `data-*` 속성

Base UI는 `data-state="open"` 하나가 아니라 **상태별 개별 속성**을 붙인다. Tailwind 셀렉터도 그에 맞춰 쓴다.

```tsx
// ✅ Base UI
<Menu.Item className="data-highlighted:bg-accent data-disabled:opacity-50">복제</Menu.Item>
<Dialog.Popup className="transition data-starting-style:opacity-0 data-ending-style:opacity-0 data-ending-style:scale-95" />

// ❌ Radix 시절 셀렉터
<Menu.Item className="data-[state=open]:bg-accent data-[highlighted]:bg-accent" />
```

주요 속성: `data-open` / `data-closed`, `data-starting-style` / `data-ending-style`(진입·퇴장 트랜지션), `data-highlighted`, `data-checked` / `data-unchecked`, `data-disabled`, `data-pressed`, `data-side`.

- 열림/닫힘 애니메이션은 keyframe 클래스(`animate-in`/`animate-out`)를 새로 만들지 말고 `transition` + `data-starting-style`/`data-ending-style` 조합으로 처리한다. **transition이 기본**인 이유는 중간에 매끄럽게 취소될 수 있어서다(빠르게 열고 닫을 때 튀지 않는다). keyframe이 꼭 필요하면 `data-open`/`data-closed`에 건다.
- Motion 같은 애니메이션 라이브러리를 쓸 때는 `Portal`에 `keepMounted`를 주고 `AnimatePresence` + `render`로 `motion.div`를 합성한다.
- 팝업 크기를 트리거에 맞춰야 하면 직접 측정하지 말고 Base UI가 `Popup`/`Positioner`에 노출하는 CSS 변수(`--anchor-width`, `--available-height` 등)를 쓴다 — 예: `className="w-[var(--anchor-width)] max-h-[var(--available-height)]"`. 변수 목록은 컴포넌트별 API 레퍼런스에 있다.

### Radix → Base UI 이관 → `references/radix-migration.md`

기존 Radix 코드를 Base UI로 옮길 때만 읽는다 — 영역별 대응표(패키지/합성/Positioner/data-속성/애니메이션)와 컴포넌트 단위 점진 이관 절차·이관 후 확인 항목 포함.

### 금지 패턴

```tsx
// ❌ 프리미티브 직접 의존 (shadcn 컴포넌트를 우회)
import * as DialogPrimitive from '@radix-ui/react-dialog'

// ❌ asChild — Base UI에는 없음
<Button asChild><Link href="/resources">이동</Link></Button>

// ❌ 링크를 Button의 render로 만들기 — shadcn Base UI Button은 role="button"을 강제해
//    앵커의 링크 역할을 덮어쓴다 (새 탭 열기·주소 복사 등 링크 동작이 죽는다)
<Button render={<Link href="/resources" />}>이동</Button>
// ✅ 링크는 buttonVariants()로 스타일만 입힌다
<Link href="/resources" className={buttonVariants({ variant: 'outline' })}>이동</Link>

// ❌ Positioner 없이 Popup에 위치 prop
<Popover.Popup side="bottom" sideOffset={8} />
```

- 단, `Menu.Item render={<Link/>}`처럼 **프리미티브 파트에 넘기는 `render`는 정상 패턴**이다 — 금지 대상은 `Button`을 링크로 만드는 경우다.

---

## 2. 디자인 토큰과 스타일 덮어쓰기

> 토큰 체계를 어떻게 나눌지·상태 색상을 어떻게 일관되게 유지할지 같은 원칙은 `design-system` 스킬 참조. 이 섹션은 그 원칙의 **Tailwind/shadcn 구현**(CSS 변수 정의·variant 확장)만 다룬다.

색·간격을 하드코딩(`bg-blue-500`)하지 않고 **토큰 유틸**(`bg-primary`, `text-muted-foreground`, `border-border`)을 쓴다. 토큰은 전역 CSS에 `:root`/`.dark` CSS 변수로 정의되고 `@theme inline`으로 Tailwind 유틸에 노출된다. 라이트/다크가 한 번에 따라오는 지점이 여기다.

### 없는 토큰이 필요할 때

기본 토큰에는 `success`/`warning`이 **없다**. `variant="success"`처럼 쓰려면 두 단계가 선행돼야 한다.

1. 전역 CSS의 `:root`와 `.dark`에 `--success` / `--success-foreground`를 oklch 값으로 정의하고, `@theme inline`에 `--color-success: var(--success)`로 노출한다.
2. 해당 컴포넌트(Badge/Button 등) 파일의 `cva` variant 목록에 항목을 추가한다.

두 단계 중 하나라도 빠지면 클래스가 조용히 무시되거나 타입 에러가 난다. 구체적인 스니펫과 기본 토큰 전체 목록 → `references/shadcn-setup.md`.

### 컴포넌트를 포크하지 않고 덮어쓰기 — `data-slot`

shadcn 프리미티브의 각 파트에는 `data-slot="..."`이 붙는다(`data-slot="drawer-overlay"`, `data-slot="input-group-control"` 등). 한 화면에서만 다르게 보여야 하는 정도라면 `ui/*` 파일을 복제·포크하지 말고 부모에서 셀렉터로 덮는다.

```tsx
<div className="[&_[data-slot=drawer-overlay]]:bg-black/80">
  <Drawer>...</Drawer>
</div>
```

- 컴포넌트 파일 자체를 고치는 것은 **프로젝트 전역으로 바꿔야 할 때만**이다. 그때도 `shadcn add`로 다시 받으면 덮어써지므로 `--diff`로 확인한다(→ §4).

---

## 3. 컴포넌트 패턴

> 아래 컴포넌트가 소비하는 데이터 훅(`useResource*` 등)의 정의는 `react-query-guide` 스킬 참조. Server/Client 경계·`'use client'`는 `nextjs-guide` 참조. 이 섹션은 그 훅을 소비하는 **UI 스타일링**만 다룬다.
> 도메인 이름(`resource`, `status` 값 등)은 자리표시자다 — 프로젝트의 실제 엔티티로 바꿔 읽는다.

### 상태 전이 액션 버튼

전이 중(`isPending` 또는 중간 상태)에는 **모든 액션을 함께 잠근다.** 개별 버튼만 막으면 연타로 모순된 요청이 나간다.

```tsx
// components/resource-actions.tsx
'use client'
export function ResourceActions({ id, status }: { id: string; status: ResourceStatus }) {
  const { mutate, isPending } = useResourceTransition(id)
  const isTransitioning = status === 'activating' || status === 'deactivating'
  const locked = isPending || isTransitioning

  return (
    <div className="flex gap-2">
      <Button onClick={() => mutate('activate')}
        disabled={status !== 'inactive' || locked}>활성화</Button>
      <Button variant="destructive" onClick={() => mutate('deactivate')}
        disabled={status !== 'active' || locked}>비활성화</Button>
      <Button variant="outline" onClick={() => mutate('restart')}
        disabled={status !== 'active' || locked}>재시작</Button>
    </div>
  )
}
```

### 상태 Badge

> 상태 → 라벨/색상 중앙 매핑·색상 단독 의존 금지 원칙은 `design-system` 스킬 참조. 아래는 그 구현 형태다.

상태값 집합은 프로젝트마다 다르다 — **중요한 것은 값이 아니라 "한 곳에서 매핑하고 라벨을 반드시 함께 준다"는 형태**다.

```tsx
const statusConfig: Record<ResourceStatus, { label: string; variant: string }> = {
  active:       { label: '활성', variant: 'success' },
  inactive:     { label: '비활성', variant: 'secondary' },
  activating:   { label: '활성화 중', variant: 'warning' },
  deactivating: { label: '비활성화 중', variant: 'warning' },
  pending:      { label: '대기', variant: 'default' },
  error:        { label: '오류', variant: 'destructive' },
}
```

- 이 매핑을 화면마다 다시 선언하지 않는다 — 한 모듈에서 export해 재사용한다.
- `variant`만 주고 `label`을 생략하지 않는다(색각 이상 사용자 대응).
- 위 예시의 `success`/`warning`은 **기본 Badge variant가 아니다** — §2대로 토큰 추가 + `cva` variant 확장을 먼저 하거나, 기본 variant(`secondary`/`outline`/`destructive`)로 좁혀 쓴다.

### 날짜·시간 포맷 — 중앙 유틸 + 타임존 명시

날짜·시간 포맷을 컴포넌트마다 인라인으로 쓰지 않고 **`@/lib/format.ts` 같은 단일 모듈로 중앙화**한다. 화면마다 포맷이 갈리는 것과, 타임존이 뷰어의 브라우저 설정에 따라 달라지는 것을 동시에 막는다.

```ts
// src/lib/format.ts — 로케일·타임존은 프로젝트가 한 번 정한다
const LOCALE = 'ko-KR';
const TIME_ZONE = 'Asia/Seoul';   // 프로젝트 기준 타임존. 사용자별 타임존이 필요하면 인자로 받는다

export const formatDate = (d: string | Date) =>
  new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium', timeZone: TIME_ZONE }).format(new Date(d));

export const formatDateTime = (d: string | Date) =>
  new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium', timeStyle: 'short', timeZone: TIME_ZONE }).format(new Date(d));
```

```ts
import { formatDate, formatDateTime } from '@/lib/format';

formatDate(resource.createdAt)      // 중앙 정의된 로케일·타임존으로 렌더
formatDateTime(resource.createdAt)
```

- **`timeZone`을 생략한 `toLocaleDateString()`/`toLocaleString()` 직접 호출 금지** — 서버(UTC)와 클라이언트(로컬)의 결과가 달라져 하이드레이션 불일치가 난다.
- 숫자 포맷(금액 천단위 등)은 `toLocaleString`으로 충분하다 — 타임존과 무관하다.

### 리스트 Client Component

```tsx
'use client'
import { TableSkeleton } from '@/components/ui/skeletons'  // 아래 "공유 스켈레톤" 참조

export function ResourceListClient() {
  const { data: resources, isLoading, error } = useResources()

  if (isLoading) return <TableSkeleton rows={6} cols={5} />  // 텍스트 "불러오는 중..." 금지
  if (error) return <p className="text-destructive">목록을 불러올 수 없습니다.</p>
  if (!resources?.length) return <p className="text-muted-foreground">등록된 항목이 없습니다.</p>

  return <table>...</table>
}
```

로딩·에러·빈 목록 **세 갈래를 각각 처리**한다(원칙 → `design-system`).

> 클라이언트 `isLoading`(캐시 없음) vs 라우트 레벨 `loading.tsx`(prefetch 대기) 역할 구분 → `nextjs-guide`.

### 공유 스켈레톤 컴포넌트

shadcn이 제공하는 것은 프리미티브 `<Skeleton />` 하나뿐이다. 화면마다 스켈레톤을 새로 조립하지 말고, **프로젝트에서 조합 컴포넌트를 한 번 만들어** 재사용한다.

```
src/components/ui/skeletons.tsx   ← 프로젝트가 직접 만드는 조합 레이어
```

| 컴포넌트 | 용도 |
|---------|------|
| `<TableSkeleton rows cols />` | 테이블 리스트 (rows/cols 조절) |
| `<CardGridSkeleton count />` | 통계/요약 카드 그리드 |
| `<PageHeaderSkeleton />` | 페이지 제목 + 설명 영역 |

- 스켈레톤은 **최종 콘텐츠의 레이아웃 형태를 유지**해야 한다(→ `design-system`). 형태가 다르면 로드 후 레이아웃 점프가 난다.
- 라우트 레벨 로딩(`loading.tsx`)에서의 조합·배치는 → `nextjs-guide`.
- 로딩 분기에서 "불러오는 중..." 텍스트는 금지.


---

## 4. 툴링 — 컴포넌트 API를 추측하지 않는다

shadcn 컴포넌트의 prop 이름·slot 구조는 버전에 따라 바뀐다. 기억에 의존해 쓰지 말고 확인한다.

- `npx shadcn@latest docs <component>` — 문서·소스·예제를 CLI에서 조회한다(`--base`, `--json`).
- `npx shadcn@latest add <component> --dry-run` / `--diff` / `--view` — 쓰기 전에 무엇이 들어오고 무엇이 덮어써지는지 본다. 커스터마이징한 컴포넌트를 다시 받을 때 필수.
- `npx shadcn@latest info` — 감지된 프레임워크·설정·설치된 컴포넌트 확인.
- `npx shadcn@latest mcp init --client claude` — shadcn MCP 서버(레지스트리 브라우즈·검색·설치).
- `npx skills add shadcn/ui` — shadcn 공식 스킬(프로젝트 컨텍스트 감지·CLI·테마·레지스트리 절차).

설정 파일 필드·CLI 플래그 전체 → `references/shadcn-setup.md`.

---

## 5. Gotchas (운영하며 축적)

- Tailwind 클래스는 **정적으로만 감지**된다 — `bg-${color}` 같은 동적 조합은 빌드에서 제거된다. 전체 클래스명을 매핑 객체로 나열한다(상태 Badge 패턴처럼).
- `render` prop에 넘긴 커스텀 컴포넌트가 ref forward/props spread를 빠뜨리면 **에러 없이** 트리거·접근성만 조용히 죽는다 — 동작이 안 하면 이것부터 확인한다.
- Portal로 뜨는 Popup은 DOM상 `body` 아래로 이동하므로 상위 컴포넌트의 상속 스타일(텍스트 색 등)을 받지 못할 수 있다 — 색·배경 토큰 클래스를 Popup에 직접 준다.
- `cn` 유틸은 독립 패키지 `cn`으로 옮겨졌다 — 새 `lib/utils.ts`는 `export { cn } from "cn"` 한 줄이다. 기억에 있는 `clsx`+`twMerge` 보일러플레이트를 손으로 다시 만들지 말고, 기존 프로젝트는 `npx shadcn@latest migrate cn`으로 전환한다(호출부 API 동일).
- shadcn Base UI `Button`은 `role="button"`을 강제한다 — `render={<Link/>}`로 링크를 만들면 링크 역할이 죽는다. 링크는 `buttonVariants()` + 평범한 `<Link>`/`<a>`로 만든다.
- Motion으로 팝업 애니메이션을 짤 때 **opacity를 변화시키지 않으면** Base UI가 애니메이션 완료를 감지하지 못해 언마운트가 지연된다 — 종료 상태에 `opacity: 0.9999` 같은 미세 변화를 넣어 감지시킨다.
- `SelectContent`는 기본값 `alignItemWithTrigger={true}`라 **선택된 항목이 트리거 위에 겹치도록** 팝업이 배치된다 — 위치 버그가 아니다. 트리거 가장자리에 맞추려면 `alignItemWithTrigger={false}`를 준다.
- 팝업 폭·높이를 JS로 측정해 맞추지 않는다 — `--anchor-width`(트리거 폭), `--available-height`(남은 공간) CSS 변수를 쓴다. 측정 코드는 리사이즈·스크롤에서 어긋난다.

> 운영 중 새로 발견한 함정은 이 섹션에 계속 축적한다.
