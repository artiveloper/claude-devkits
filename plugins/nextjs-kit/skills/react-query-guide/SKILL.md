---
name: react-query-guide
description: >
  React Query 데이터 레이어 가이드 — 도메인 디렉토리 구조, query keys/options/prefetch,
  useMutation + invalidate/낙관적 업데이트, Server Actions(ActionResult 봉투), 실시간 구독 흡수, 상태 소유권 판단.
  React Query, TanStack Query, query key, prefetch, mutation, invalidate, 낙관적 업데이트,
  URL 상태/전역 상태 도구 선택, 신규 feature 데이터 레이어 추가 시 사용.
  UI 스타일링(shadcn-ui)과 라우팅·Server/Client 경계(nextjs-guide)는 다루지 않는다.
---

# React Query — 데이터 레이어 패턴

> UI/컴포넌트/Tailwind·shadcn 구현 → `shadcn-ui` 스킬 참조
> Server/Client 경계·`loading.tsx`·route group → `nextjs-guide` 스킬 참조
> 프레임워크 불문 원칙(상태 4분류·컴포넌트 경계·롤백 필수) → `frontend-architecture` 스킬 참조.
> **frontend-kit 미설치 시**: 이 문서에 나오는 `frontend-architecture` 참조는 전부 건너뛴다. `backend-architecture` 참조도 backend-kit 설치 시에만 유효하다 — 없는 스킬을 찾거나 로드하려 하지 않는다.

**백엔드는 자리표시자다.** 아래 예시는 Server Action 안에서 `db`라는 데이터 접근 모듈을 호출한다 — Supabase·Prisma·REST 클라이언트 등 프로젝트가 쓰는 것으로 바꿔 읽는다. 도메인 이름(`resource`, `item`)도 마찬가지다.

---

## 1. 도메인 디렉토리 구조 (권장)

기능별(feature-based) 구조의 한 구현 형태다(원칙 → `frontend-architecture`). 프로젝트에 이미 다른 컨벤션이 자리 잡았으면 그쪽을 따르되, **한 프로젝트 안에서는 하나로 통일**한다.

```
src/domain/{feature}/
├── index.ts                    — public API (전체 re-export)
├── types/
│   ├── index.ts
│   ├── dto.ts                  — API 요청/응답 타입
│   └── entity.ts               — 도메인 엔티티
├── queries/
│   ├── index.ts
│   ├── {feature}.query-keys.ts
│   ├── {feature}.query-options.ts
│   └── {feature}.prefetch.ts
├── hooks/
│   ├── index.ts
│   └── {feature}.hooks.ts
├── actions/
│   └── {feature}.actions.ts    — 'use server'
└── validations/
    └── {feature}.validations.ts — 스키마 검증 (Server Action + Form 공유)
```

레이어 규칙:
- 크로스 도메인 deep import 금지: `@/domain/resources/queries/...` ❌ → `@/domain/resources` ✅
- `actions/`, `service/`, `validations/`에는 `index.ts` 불필요 (루트에서 직접 export)
- 검증 스키마는 해당 도메인의 `validations/{feature}.validations.ts`에 둔다. 앱 루트 `lib/`는 여러 도메인이 실제로 공유하는 것만 남긴다(예: 공통 ActionResult 봉투, 인증 헬퍼, 공용 포맷터).

---

## 1-1. 복잡도별 적용 범위 (풀세트 여부 판단)

모든 feature에 `queries/hooks/actions/validations` 풀세트를 기계적으로 만들지 않는다. 신규 feature마다 아래 기준으로 먼저 적용 범위를 판단한다:

```
신규 기능 추가 → 읽기 전용인가?
                     ↓ Yes: queries/ (keys+options+prefetch) + hooks/(useQuery)만. actions/validations 생략
                     ↓ No: 서버 상태 변경(mutation)이 있는가?
                              ↓ 단순 CRUD, 인증/소유권 등 비즈니스 룰 없음: + actions/(ActionResult) + validations/(스키마)
                              ↓ 인증·소유권·쿼터 등 비즈니스 룰 있음, 또는 재사용 필요: 위 전체 + 5-1절(순수 로직 분리) + 4절(낙관적 업데이트) 적용
```

예:
- 참조용 목록(조회만) → `queries/` + `hooks/`. `actions/`/`validations/` 불필요.
- 단순 CRUD 엔티티(특별한 룰 없음) → 풀세트, 5절 기본 패턴으로 충분.
- 상태 전이 + 실시간 반영이 있는 엔티티 → 풀세트 + 5-1절 + 4절 낙관적 업데이트 필수.

빈 `actions/`·`validations/` 폴더를 미리 만들어두는 것은 과설계다 — 쓰기 기능이 실제로 추가될 때 그 시점에 만든다.

---

## 2. Query Keys & Options

```ts
// {feature}.query-keys.ts
export const resourceQueryKeys = {
  all: ['resources'] as const,
  list: () => [...resourceQueryKeys.all, 'list'] as const,
  detail: (id: string) => [...resourceQueryKeys.all, 'detail', id] as const,
}

// {feature}.query-options.ts
export const resourceQueryOptions = {
  list: () => ({
    queryKey: resourceQueryKeys.list(),
    queryFn: () => fetchResources(),
  }),
  detail: (id: string) => ({
    queryKey: resourceQueryKeys.detail(id),
    queryFn: () => fetchResource(id),
    staleTime: 30_000,
  }),
}
```

금지:
```ts
// ❌ 인라인 queryKey — 무효화 시점에 키가 어긋나 캐시가 안 지워진다
useQuery({ queryKey: ['resources'], queryFn: fetchResources })

// ✅ options 팩토리 사용
useQuery(resourceQueryOptions.list())
```

---

## 3. Prefetch (Server Component)

`runPrefetch`/`getQueryClient`는 프로젝트가 한 번 정의하는 얇은 헬퍼다 — 아래 형태를 그대로 두고 쓰면 된다.

```ts
// {feature}.prefetch.ts
export const resourcePrefetch = {
  list: () => async (queryClient: QueryClient) => {
    await queryClient.prefetchQuery(resourceQueryOptions.list())
  },
}

// lib/react-query/prefetch.ts
export async function runPrefetch(...prefetchers: Array<(qc: QueryClient) => Promise<void>>) {
  const qc = getQueryClient()
  await Promise.all(prefetchers.map(fn => fn(qc)))   // 병렬 — 워터폴 방지
  return dehydrate(qc)
}

// app/(dashboard)/resources/page.tsx — Server Component
export default async function ResourcesPage() {
  const state = await runPrefetch(resourcePrefetch.list())
  return (
    <HydrationBoundary state={state}>
      <ResourceListClient />
    </HydrationBoundary>
  )
}
```

---

## 4. Mutation + Invalidation

```ts
// {feature}.hooks.ts

// 단순 CRUD mutation
export function useCreateItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createItemAction,             // Server Action
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.list() })
      toast.success('추가되었습니다.')
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : '오류가 발생했습니다.'),
  })
}

// 낙관적 업데이트 — 상태 전이처럼 즉시 반영이 필요한 경우
export function useResourceTransition(resourceId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (action: 'activate' | 'deactivate' | 'restart') =>
      transitionResourceAction(resourceId, action),
    onMutate: async (action) => {
      await queryClient.cancelQueries({ queryKey: resourceQueryKeys.detail(resourceId) })
      const previous = queryClient.getQueryData(resourceQueryKeys.detail(resourceId))
      queryClient.setQueryData(resourceQueryKeys.detail(resourceId), (old: Resource) => ({
        ...old,
        status: action === 'activate' ? 'activating' : 'deactivating',
      }))
      return { previous }                          // ← 롤백용 스냅샷
    },
    onError: (_err, _action, context) => {
      queryClient.setQueryData(resourceQueryKeys.detail(resourceId), context?.previous)  // ← 롤백
      toast.error('요청을 처리하지 못했습니다.')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: resourceQueryKeys.detail(resourceId) })  // ← 서버 확정값으로 재조정
    },
  })
}
```

- `onMutate`에서 스냅샷을 반환하지 않으면 롤백이 불가능하다 — **롤백 없는 낙관적 업데이트는 결함**(→ `frontend-architecture`).
- `onSettled`의 invalidate를 생략하면 낙관적으로 그린 값이 서버 확정값과 영구히 어긋날 수 있다.

금지:
```ts
// ❌ router.refresh()로 서버 상태 갱신
await fetch('/api/items', { method: 'POST' })
router.refresh()

// ❌ useEffect에서 fetch (경쟁 조건 + 캐시 없음)
useEffect(() => { fetch('/api/resources').then(...) }, [])
```

---

## 5. Server Actions (ActionResult 패턴)

```ts
// {feature}.actions.ts
'use server'

type ActionResult<T = void> =
  | { success: true; data: T }
  | { success: false; error: string }

export async function createItemAction(input: CreateItemInput): Promise<ActionResult<Item>> {
  const user = await getCurrentUser()                    // 프로젝트의 인증 헬퍼
  if (!user) throw new Error('로그인이 필요합니다.')      // 인증 에러 → throw

  try {
    const row = await db.items.insert({ ...input, ownerId: user.id })   // 프로젝트의 데이터 접근 모듈
    return { success: true, data: toItem(row) }
  } catch {
    return { success: false, error: '항목을 추가하지 못했습니다.' }
  }
}
```

규칙:
- 인증 에러 → `throw new Error(...)` (React Query가 error state로 처리)
- 비즈니스 에러 → `ActionResult.error` (사용자 친화 메시지)
- 원본 Error 객체·스택·드라이버 메시지를 클라이언트에 그대로 노출 ❌ (backend-kit이 설치돼 있으면 세부 원칙은 `backend-architecture` 참조)
- 인가·소유권 검증은 클라이언트가 아니라 **이 서버 경계에서** 한다.

---

## 5-1. 순수 로직 분리 (재사용성·테스트 용이성)

1-1절에서 비즈니스 룰이 있다고 판단된 액션, 또는 API route·cron job·유닛 테스트에서 재사용이 실제로 필요한 액션은, 파일 상단 `'use server'` 대신 **함수 단위 `'use server'`**로 좁혀서 순수 로직과 Server Action 진입점을 분리한다.

```ts
// {feature}.actions.ts

// 순수 로직 — 'use server' 없음. API route/cron/유닛 테스트에서 직접 import해 재사용 가능
export async function createItem(input: CreateItemInput): Promise<ActionResult<Item>> {
  const user = await getCurrentUser()
  if (!user) throw new Error('로그인이 필요합니다.')

  try {
    const row = await db.items.insert({ ...input, ownerId: user.id })
    return { success: true, data: toItem(row) }
  } catch {
    return { success: false, error: '항목을 추가하지 못했습니다.' }
  }
}

// Server Action 진입점 — 폼/useMutation이 호출하는 얇은 wrapper만 'use server'
export async function createItemAction(input: CreateItemInput) {
  'use server'
  return createItem(input)
}
```

- `hooks/`의 `mutationFn`은 wrapper(`createItemAction`)를 호출한다. 순수 함수(`createItem`)를 클라이언트에서 직접 참조하지 않는다.
- 단순 CRUD·재사용 계획 없는 액션까지 전부 이렇게 분리하지 않는다 — 5절 기본 패턴으로 충분하면 그대로 둔다.

---

## 5-2. 검증 스키마 공유 (클라이언트 폼 ↔ Server Action)

검증 스키마는 `validations/{feature}.validations.ts`에 두고, **클라이언트 폼과 Server Action이 동일 스키마를 import해 쓴다.** 같은 규칙이 양쪽에 각각 작성되는 것을 막는다 (`frontend-architecture`의 "폼 검증 이중화" 원칙 구현).

```ts
// domain/{feature}/validations/{feature}.validations.ts
import { z } from 'zod'

export const createItemSchema = z.object({
  title: z.string().min(1, '제목을 입력하세요'),
  description: z.string().optional(),
})

export type CreateItemInput = z.infer<typeof createItemSchema>
```

**클라이언트 폼** — `zodResolver`로 연결:

```tsx
'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { createItemSchema, type CreateItemInput } from '@/domain/items'
import { useCreateItem } from '@/domain/items'

export function ItemForm() {
  const { mutate, isPending } = useCreateItem()
  const form = useForm<CreateItemInput>({
    resolver: zodResolver(createItemSchema),
    defaultValues: { title: '', description: '' },
  })

  return (
    <form onSubmit={form.handleSubmit((data) => mutate(data))}>
      {/* 폼 필드 — UI 구현은 shadcn-ui 스킬 참조 */}
    </form>
  )
}
```

**Server Action** — 서버에서 재검증:

```ts
// {feature}.actions.ts
'use server'
import { createItemSchema } from '@/domain/items'

export async function createItemAction(input: unknown): Promise<ActionResult<Item>> {
  const parsed = createItemSchema.safeParse(input)
  if (!parsed.success) return { success: false, error: parsed.error.issues[0].message }
  // ... 비즈니스 로직
}
```

규칙:
- 스키마는 `domain/{feature}/` 안에 둔다 — 여러 feature가 실제로 공유하는 것만 `lib/`에 올린다.
- 클라이언트 검증은 즉각 피드백(UX)용이고 신뢰 경계가 아니다 — **서버 재검증이 최종 관문**이다.
- Server Action에 넘어온 `input`은 타입 단언 없이 `unknown`으로 받고 `safeParse`로 검증한다.

---

## 6. 실시간 구독 → React Query 캐시

실시간 채널(WebSocket, SSE, BaaS의 realtime 등)을 쓴다면 **별도 상태 저장소를 만들지 말고 React Query 캐시에 흡수**시킨다. 그래야 UI의 단일 출처가 유지된다.

```ts
// hooks/use-resource-realtime.ts
export function useResourceRealtime(resourceId: string) {
  const queryClient = useQueryClient()
  useEffect(() => {
    const unsubscribe = subscribeToResource(resourceId, (next) => {   // 프로젝트의 실시간 클라이언트
      queryClient.setQueryData(resourceQueryKeys.detail(resourceId), toResource(next))
      queryClient.invalidateQueries({ queryKey: resourceQueryKeys.list() })
    })
    return () => { unsubscribe() }     // cleanup 필수 — 없으면 구독이 누적된다
  }, [resourceId, queryClient])
}
```

- 상세는 `setQueryData`로 즉시 반영하고, 목록은 `invalidateQueries`로 재검증하는 조합이 일반적이다.
- cleanup 누락은 라우트 이동마다 구독이 쌓여 메모리 누수·중복 갱신을 만든다.

---

## 7. 캐시 레이어 요약 (Next.js App Router 기준)

| 레이어 | 역할 |
|--------|------|
| Next.js fetch cache | ISR/revalidateTag. 클라이언트 freshness 용도 ❌ |
| React cache() | 단일 RSC 렌더 내 중복 fetch 제거 |
| React Query cache | UI 상태 단일 출처. 모든 UI는 여기서만 읽음 |

---

## 8. 상태 소유권 (어디에 둘 것인가)

| 상태 유형 | 도구 | 비고 |
|----------|------|------|
| 서버 데이터 | **React Query** | 캐싱·invalidate·낙관적 업데이트. 모든 서버 상태의 단일 출처 |
| URL 상태 (필터·정렬·페이지네이션·탭) | **URL 쿼리 동기화 라이브러리** (예: `nuqs`) | 공유·새로고침·뒤로가기 보존 |
| 로컬 UI 상태 | `useState`/`useReducer` | 한 컴포넌트 내부(모달 open, 입력값 등) |
| 전역 클라이언트 상태 | **전역 스토어 (기본 보류)** | 아래 기준 충족 전까지 도입하지 않는다 |

**판단 흐름:** 서버 데이터? → React Query / URL에서 복원해야 하나(필터·페이지)? → URL 상태 / 한 컴포넌트 내부? → useState.

**URL 상태 규칙:**
- 목록 필터·검색·정렬·페이지·탭은 `useState` 대신 URL에 둔다 (`router.refresh()` 금지 규칙과 무관 — URL 변경은 정상).
- URL 값을 React Query `queryKey`에 포함해 필터 변경 시 자동 리페치 (인라인 queryKey 금지 규칙대로 query options 팩토리에 파라미터로 전달).
- Server Component에서 초기값은 `searchParams`로 읽어 prefetch에 반영 → 클라이언트가 이어받는다.
- **검색 입력은 디바운스**(약 300ms) 후 URL/`queryKey`에 반영 — 매 키 입력마다 리페치 금지.
- **긴 목록은 페이지네이션이 1차 해법.** 가상화(`@tanstack/react-virtual` 등)는 페이지네이션으로도 부족한 1000+ 단일 뷰가 실제로 필요할 때만 도입한다.

**전역 스토어(Zustand 등)는 다음 중 하나가 실제로 생기기 전까지 도입하지 않는다:**
- 부모-자식이 아닌, 멀리 떨어진 컴포넌트 간 공유되는 **순수 클라이언트** 상태 (예: 목록 일괄 선택 → 툴바와 테이블이 선택셋 공유)
- 라우트를 가로지르는 멀티스텝 위저드 상태 (URL로 표현하기 부적합한 경우)

서버 상태(React Query)·URL 상태·로컬 상태(useState)로 해결되면 전역 스토어를 추가하지 않는다. 실시간 데이터는 6절대로 `setQueryData`로 React Query에 흡수되므로 전역 스토어 대상이 아니다.

> 위 도구 이름은 예시다. 프로젝트에 아직 없는 라이브러리를 이 문서를 근거로 설치하지 않는다 — **먼저 `package.json`을 확인**하고, 없으면 도입 여부부터 판단한다.

---

## 9. 구현 순서

0. 적용 범위 판단(1-1절) — 이 feature에 어떤 하위 폴더가 실제로 필요한지 먼저 결정
1. `lib/react-query/` — `getQueryClient`, `runPrefetch`, `QueryProvider` (최초 1회)

   ```tsx
   // lib/react-query/query-provider.tsx
   'use client'
   import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
   import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
   import { useState } from 'react'

   export function QueryProvider({ children }: { children: React.ReactNode }) {
     const [queryClient] = useState(
       () => new QueryClient({
         defaultOptions: { queries: { staleTime: 60_000 } },
       })
     )
     return (
       <QueryClientProvider client={queryClient}>
         {children}
         <ReactQueryDevtools initialIsOpen={false} />
       </QueryClientProvider>
     )
   }
   ```

2. `domain/{feature}/queries/` — keys → options → prefetch
3. `domain/{feature}/actions/` — Server Actions (ActionResult 패턴)
4. `domain/{feature}/hooks/` — `useQuery` / `useMutation` 래퍼
5. `domain/{feature}/index.ts` — public API re-export
6. Page (Server Component) — `runPrefetch` + `HydrationBoundary`
7. Client Components — hooks 사용, UI만 담당 (→ UI 구현은 `shadcn-ui` 스킬)

---

## 10. 기존 코드베이스에 도입할 때

- 데이터 로딩용 `router.refresh()`는 제거 대상이다 — 서버 상태 갱신은 `invalidateQueries`가 담당한다. 세션 갱신(로그인/로그아웃)용 `router.refresh()`는 남겨둔다.
- **feature 단위로 전환하고, 전환이 끝난 feature부터 위 규칙을 예외 없이 적용한다.** 전환 중인 코드와 완료된 코드에 같은 잣대를 들이대면 리뷰가 마비된다 — 어느 feature가 전환 완료인지 프로젝트가 명시적으로 기록한다.
- 페이지만 있고 도메인 레이어가 없는 화면이 남아 있다면 그게 다음 전환 후보다.
- 한 번에 전면 전환하지 않는다. 새로 추가되는 feature부터 이 패턴으로 쓰는 것이 가장 비용이 낮다.


---

## 11. Gotchas (운영하며 축적)

- prefetch한 데이터도 `staleTime`이 기본값(0)이면 **hydration 직후 즉시 리페치**된다 — prefetch 효과를 보려면 query options에 의미 있는 `staleTime`을 설정한다.
- `invalidateQueries`는 기본이 **prefix 매칭**이다 — `queryKeys.all`을 무효화하면 list/detail 전부 무효화된다. 의도한 범위인지 확인한다.
- Server Action은 병렬로 호출해도 **순차 실행**된다 — 다건 조회를 Server Action `queryFn`으로 병렬 요청하면 워터폴이 된다. 조회가 많으면 Route Handler 경로를 검토한다.
- `mutateAsync`를 쓰면서 `onError` 콜백에만 의존하면 unhandled rejection이 난다 — `mutateAsync`는 호출부에서 try/catch 한다.
- `QueryClient`를 컴포넌트 바깥(`const queryClient = new QueryClient()`)이나 `useState(() => ...)` 없이 만들면 렌더마다 인스턴스가 재생성된다 — devtools 연결이 끊기거나 캐시가 초기화된다. 반드시 `useState(() => new QueryClient(...))` 형태를 쓴다.

> 운영 중 새로 발견한 함정은 이 섹션에 계속 축적한다.
