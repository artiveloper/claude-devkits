---
name: nextjs-guide
description: >
  Next.js App Router 메커니즘 가이드 — 파일 컨벤션(page/layout/loading/error), Server vs Client 경계와 합성,
  loading.tsx + Suspense 스트리밍, 서버 데이터 보안(DAL/DTO, server-only, Server Action 재인가),
  캐시·렌더링 모델, 에러 처리, proxy.ts와 matcher, Next.js 16 기준선.
  Next.js, App Router, RSC, 'use client', server-only, Server Action, loading.tsx, error.tsx, Suspense,
  middleware, proxy.ts, matcher, use cache, Next.js 16 관련 작업 시 사용.
  클라이언트 데이터 캐싱 구현(react-query-guide)과 UI 스타일링(shadcn-ui)은 다루지 않는다.
---

# Next.js — App Router 메커니즘

> UI 스타일링(모바일 퍼스트·shadcn 컴포넌트·스켈레톤) → `shadcn-ui` 스킬 참조
> 데이터 레이어(서버 상태 캐싱·prefetch·mutation) → `react-query-guide` 스킬 참조
> 프레임워크 불문 구조 원칙(상태 분류·컴포넌트 경계) → `frontend-architecture` 스킬 참조.
> **frontend-kit 미설치 시**: 이 문서에 나오는 `frontend-architecture`·`design-system` 참조는 전부 건너뛴다 — 없는 스킬을 찾거나 로드하려 하지 않는다.

아래 예시의 도메인 이름(`resources` 등)은 자리표시자다 — 프로젝트의 실제 리소스명으로 바꿔 읽는다.

---

## 1. App Router 파일 컨벤션

```
src/app/(dashboard)/
├── layout.tsx                  — 공유 레이아웃 (Server Component)
├── loading.tsx                 — 대시보드 홈 라우트 로딩
├── resources/
│   ├── page.tsx                — Server Component (prefetch + HydrationBoundary)
│   ├── loading.tsx             — 세그먼트 로딩
│   └── [id]/page.tsx           — 동적 세그먼트
└── settings/{page,loading}.tsx

src/proxy.ts                    — 요청 앞단 (구 middleware.ts) — app/과 같은 레벨
```

- `(dashboard)` 같은 **route group**은 URL에 노출되지 않는 그룹 — 공유 layout 적용용.
- 특수 파일: `page`(라우트 진입), `layout`(공유 껍데기), `loading`(세그먼트 로딩 UI), `error`(에러 바운더리).
- `proxy.ts`는 세그먼트 파일이 아니라 **프로젝트 루트(또는 `src/`)** 에 하나만 둔다 (→ 5절).

---

## 2. Server Component vs Client Component

기본은 **Server Component**. `'use client'`는 아래가 필요할 때만 붙인다.
- 브라우저 상호작용/이벤트 핸들러, `useState`/`useEffect` 등 훅
- 클라이언트 데이터 훅(`useQuery`/`useMutation` 등) 소비

경계 규칙:
- **데이터 fetch는 Server Component에서 prefetch** → `HydrationBoundary`로 Client에 전달 (→ `react-query-guide` 3절).
- **UI 상호작용·데이터 훅 소비는 Client Component**가 담당 (컴포넌트 스타일링은 → `shadcn-ui`).
- UI 컴포넌트에서 `fetch`/`useEffect`로 직접 패칭 금지 → 도메인 훅 사용 (→ `react-query-guide`).

```tsx
// app/(dashboard)/resources/page.tsx — Server Component
export default async function ResourcesPage() {
  const state = await runPrefetch(resourcePrefetch.list())   // ← 헬퍼 정의는 react-query-guide 3절
  return (
    <HydrationBoundary state={state}>
      <ResourceListClient />                                  {/* 'use client' */}
    </HydrationBoundary>
  )
}
```

### 합성 규칙

- **`'use client'`는 최대한 아래로.** 레이아웃 전체가 아니라 상호작용하는 조각에만 붙인다 — 그 파일이 import하는 모든 것이 클라이언트 번들로 끌려간다.
- **Server Component를 Client Component의 `children`/props로 넘길 수 있다.** 이렇게 넘긴 것은 클라이언트 모듈 그래프에 포함되지 않고 서버에서 렌더된 결과로 전달된다 — Client인 `<Modal>` 안에 Server인 `<Cart>`를 넣는 식.
- **Context Provider는 트리 아래쪽에 둔다.** `<html>` 전체가 아니라 `{children}`만 감싼다 — 정적 최적화 여지를 남긴다.
- **클라이언트 전용 서드파티**는 `'use client'` 한 줄짜리 파일로 래핑해 re-export한 뒤 Server Component에서 쓴다.
- 서버 전용 모듈에는 **`import 'server-only'`** 를 붙인다 — 클라이언트에서 import되면 빌드 타임에 실패한다 (→ 5절).

---

## 3. 라우트 레벨 로딩 (loading.tsx)

라우트 레벨 로딩(서버 prefetch 중)은 **`loading.tsx`** 로 처리한다. Next.js가 해당 세그먼트를 자동으로 `<Suspense>`로 감싸므로 prefetch 완료 전까지 로딩 UI가 표시된다(스트리밍).

```tsx
// app/(dashboard)/resources/loading.tsx
import { Skeleton } from '@/components/ui/skeleton';
import { TableSkeleton, PageHeaderSkeleton } from '@/components/ui/skeletons';  // 프로젝트 공유 스켈레톤 → shadcn-ui

export default function ResourcesLoading() {
  return (
    <div>
      <PageHeaderSkeleton />
      <div className="space-y-4">
        <div className="flex gap-3">
          <Skeleton className="h-9 w-28 rounded-md" />
        </div>
        <TableSkeleton rows={6} cols={5} />
      </div>
    </div>
  );
}
```

**역할 구분:**
- `loading.tsx` — **라우트 전환 시**(서버 prefetch 대기) 세그먼트 로딩. Next.js Suspense가 처리.
- 클라이언트 `isLoading` 분기 — 클라이언트 캐시가 비어 브라우저에서 fetch할 때. (→ `shadcn-ui` 리스트 컴포넌트)
- 두 경우 모두 로딩 UI는 스켈레톤을 쓰고 "불러오는 중..." 텍스트는 금지 (원칙 → `design-system`, 컴포넌트 → `shadcn-ui`).

---

## 4. 데이터 페칭·캐시 경계

**`fetch`는 기본적으로 캐시되지 않는다.** 캐시 없이 두면 완료될 때까지 렌더가 막히므로, 둘 중 하나를 고른다 —
`use cache`로 감싸거나, 컴포넌트를 `<Suspense>`로 감싸 요청 시점에 스트리밍한다.

```tsx
// ❌ 순차 — getAlbums가 getArtist를 기다린다
const artist = await getArtist(username)
const albums = await getAlbums(username)

// ✅ 병렬 — 두 요청이 동시에 출발한다
const [artist, albums] = await Promise.all([getArtist(username), getAlbums(username)])
```

- 동일한 `fetch` 요청은 한 요청 안에서 자동 메모된다. **ORM·DB 쿼리는 자동 메모가 없으므로** `React.cache`로 감싼다 — 요청 스코프 한정이고 요청 간 공유는 없다.
- `Promise.all`은 하나만 실패해도 전체가 실패한다 — 부분 실패를 허용하려면 `Promise.allSettled`.
- 레이아웃과 페이지는 세그먼트별로 병렬 렌더된다.

클라이언트 데이터 캐시 라이브러리를 쓴다면 **클라이언트 freshness의 단일 출처는 그 라이브러리**이고,
Next.js 캐시는 ISR/무효화 용도이지 UI 상태 소스가 아니다. 상세 표·상태 소유권은 → `react-query-guide` 7·8절.

`cacheComponents: true`(PPR)를 켜는 프로젝트의 `use cache`·`cacheLife`·정적 셸 극대화 → `references/cache-components.md`.

---

## 5. 서버 데이터 보안

> RSC는 데이터 접근 위치를 바꾼다 — 서버에서 읽은 것이 무심코 클라이언트로 넘어갈 수 있다.

### 읽기 — DAL + DTO

신규 프로젝트는 **Data Access Layer**를 둔다. 서버에서만 돌고, 인가를 수행하고, **필요한 필드만** 담은 DTO를 반환한다.

```ts
// data/user-dto.ts
import 'server-only'

export async function getProfileDTO(slug: string) {
  const user = await db.user.findUnique({ where: { slug } })
  const viewer = await getCurrentUser()          // React.cache로 감싼 헬퍼
  return {                                        // 전체 레코드가 아니라 공개 가능한 필드만
    username: user.username,
    phone: canSeePhone(viewer, user) ? user.phone : null,
  }
}
```

- `process.env` 접근은 DAL 안으로 모은다 — 비밀값이 다른 레이어로 새지 않는다.
- Server Component에서 DB 레코드를 통째로 Client Component에 넘기지 않는다. **props 타입이 넓으면 그만큼 다 넘어간다.**
- 세 가지 접근(기존 HTTP API 호출 / DAL / 컴포넌트 직접 쿼리) 중 **하나를 골라 섞지 않는다.** 감사 가능성이 달라진다.
- 추가 방어층으로 React Taint API(`experimental.taint`)를 켤 수 있지만, DAL에서 거르는 것이 먼저다.

### 쓰기 — Server Action

**export된 Server Action은 UI를 거치지 않고 직접 POST로 호출될 수 있다.** 페이지 레벨 인증은 Action에 전파되지 않는다.

```ts
'use server'

export async function deletePost(postId: string) {
  const session = await auth()
  if (!session?.user) throw new Error('Unauthorized')       // 인증

  const post = await db.post.findUnique({ where: { id: postId } })
  if (post.authorId !== session.user.id) throw new Error('Forbidden')   // 인가 — 소유권(IDOR 방지)

  await db.post.delete({ where: { id: postId } })
  return { success: true }                                   // 레코드 통째로 반환 금지
}
```

- **인증만이 아니라 인가**를 확인한다 — "로그인했는가"와 "이 리소스를 만질 권한이 있는가"는 다르다.
- 반환값은 직렬화돼 클라이언트로 간다 — UI에 필요한 것만 반환한다.
- `searchParams`·`params`·form 데이터·헤더는 전부 사용자 입력이다. 검증 없이 분기하지 않는다.
- **렌더 중에 mutation하지 않는다** — 쿠키 삭제·캐시 무효화를 `page.tsx` 렌더 경로에 넣지 않고 Server Action으로 옮긴다.
- 컴포넌트 안에 정의한 Action의 클로저 변수는 클라이언트를 왕복한다(Next.js가 암호화하지만 **암호화에 의존하지 않는다**).

### 감사 시 볼 곳

`'use client'` 파일의 props 타입 / `'use server'` 파일의 입력 검증·재인가·반환값 / `[param]` 폴더의 파라미터 검증 / `proxy.ts`·`route.ts`.

---

## 6. 에러 처리

**예상되는 에러는 throw하지 않고 반환값으로 모델링한다.** 폼 검증 실패, 요청 실패 등이 여기 해당한다.

```ts
'use server'
export async function createPost(prevState, formData: FormData) {
  const res = await fetch('...', { method: 'POST', body: formData })
  if (!res.ok) return { message: '생성에 실패했습니다' }   // throw 아님
}
// 클라이언트: const [state, formAction, pending] = useActionState(createPost, initialState)
```

**예상 못 한 예외**는 throw해서 에러 바운더리가 받게 한다.

| 파일 | 범위 |
|------|------|
| `error.tsx` | 해당 세그먼트. **반드시 `'use client'`**. `{ error, retry }` props |
| `global-error.tsx` | 루트 레이아웃까지 대체 — 자체 `<html>`·`<body>` 필요 |
| `not-found.tsx` + `notFound()` | 404 UI |

- 에러는 가장 가까운 상위 바운더리로 버블링된다 — 세그먼트별로 `error.tsx`를 두면 세밀하게 격리된다.
- 컴포넌트 단위로 감싸려면 `catchError`(`next/error`)로 바운더리 컴포넌트를 만든다.
- **에러 바운더리는 이벤트 핸들러의 에러를 잡지 않는다.** 렌더 중 에러만 잡는다 — 핸들러에서는 직접 `try/catch` 후 `useState`로 표시한다. 단, `startTransition` 안에서 throw된 것은 바운더리로 올라간다.

---

## 7. proxy.ts (구 middleware.ts)

Next.js 16에서 `middleware.ts` → **`proxy.ts`** (함수명도 `middleware` → `proxy`)로 리네임됐다.
기존 이름은 deprecated지만 동작한다. 코드모드로 옮긴다.

```bash
npx @next/codemod@canary middleware-to-proxy .
```

```ts
// src/proxy.ts  — app/ 과 같은 레벨
import { NextResponse, type NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
  return NextResponse.next()
}

export const config = {
  // matcher 없으면 _next/static·public 자산까지 전부 통과한다 — 반드시 제외한다
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
```

- **런타임이 Node.js가 기본**이 됐다. `runtime` 설정 옵션은 proxy에서 사용할 수 없고, 넣으면 에러가 난다.
- `skipMiddlewareUrlNormalize` → `skipProxyUrlNormalize`로 함께 리네임됐다.
- matcher 값은 빌드 타임에 정적 분석되므로 **변수를 쓸 수 없다**.

**인가를 여기서 끝내지 않는다.** Server Action은 해당 라우트로의 POST로 처리되므로,
matcher에서 그 경로가 빠지거나 Server Action을 다른 라우트로 옮기면 보호가 **조용히** 사라진다.
인증·인가는 각 Server Action·Route Handler 안에서 다시 확인한다.
(Supabase 세션 토큰 갱신을 proxy에 두는 패턴은 `supabase-guide` 소관 — **supabase-kit 미설치 시 건너뛴다**.)

---

## 8. Next.js 16 기준선

이 문서는 **Next.js 16** 기준이다. 코드를 읽다 아래가 보이면 15 이하 기준이므로 확인이 필요하다.

| 15 이하에서 보이던 것 | 16 |
|----------------------|-----|
| `middleware.ts` / `export function middleware` | `proxy.ts` / `export function proxy` (7절) |
| `const { slug } = params` (동기) | 동기 접근 **제거** — `await params` 필수 |
| `next dev --turbopack` | Turbopack이 기본 |
| `next lint` | 제거 — ESLint/Biome 직접 실행 |
| `experimental.ppr` / `experimental_ppr` | `cacheComponents: true` |
| `revalidateTag('posts')` | 두 번째 인자 필수 — `revalidateTag('posts', 'max')` |

업그레이드 절차·전체 깨지는 변경·제거 목록 → `references/nextjs-16-baseline.md`.

---

## Gotchas (운영하며 축적)

- `'use client'`는 컴포넌트가 아니라 **모듈 경계 선언**이다 — 그 파일이 import하는 모든 모듈이 클라이언트 번들로 끌려간다. 경계 파일은 얇게 유지한다.
- Server Component는 Client Component에 함수(이벤트 핸들러)를 props로 넘길 수 없다 — 직렬화 가능한 값만. 핸들러가 필요한 지점부터가 Client 경계다.
- `params`/`searchParams`/`cookies()`/`headers()`는 **Promise**다 — 15에서는 동기 접근이 경고만 내고 동작했지만 **16에서 완전히 제거**됐다. 옛 코드를 옮길 때 가장 많이 걸리는 지점이다.
- `loading.tsx`는 세그먼트의 `page`만 감싼다 — layout은 유지된 채 콘텐츠 영역만 로딩 UI로 바뀐다. 전체 화면 로딩을 기대하면 어긋난다.
- **layout이 런타임/비캐시 데이터에 접근하면 같은 세그먼트의 `loading.tsx`로 폴백하지 않는다** — 레이아웃 렌더가 끝날 때까지 내비게이션 자체가 막힌다. 그 접근을 별도 `<Suspense>`로 감싸거나 `page.tsx`로 내린다.
- proxy의 matcher에서 `_next/data`를 제외해도 **여전히 호출된다** — 페이지만 보호하고 데이터 라우트를 빠뜨리는 사고를 막으려는 의도된 동작이다.

> 운영 중 새로 발견한 함정은 이 섹션에 계속 축적한다.
