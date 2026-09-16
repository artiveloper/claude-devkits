# Cache Components (`use cache` · PPR)

> `nextjs-guide` 스킬의 참조 문서. `cacheComponents: true`를 켜거나 켤지 판단할 때만 읽는다.
> 켜지 않은 프로젝트라면 SKILL.md의 캐시 절만으로 충분하다.

## 목차
1. [무엇이 달라지는가](#무엇이-달라지는가)
2. [use cache](#use-cache)
3. [런타임 API 다루기](#런타임-api-다루기)
4. [정적 셸 극대화](#정적-셸-극대화)

## 무엇이 달라지는가

```ts
// next.config.ts
const nextConfig = { cacheComponents: true }
```

켜면 **Partial Prerendering(PPR)** 이 기본 렌더링 모델이 된다. 빌드 타임에 라우트 트리를 렌더해
**정적 셸**(HTML + RSC 페이로드)을 만들고, 캐시되지 않은 부분만 요청 시점에 스트리밍한다.

핵심 변화: `cookies()`를 읽어도 **라우트 전체가 동적으로 떨어지지 않는다.** 그 접근만 Suspense 경계 뒤로 들어간다.

> 옵트인은 이름만 바꾸는 변경이 아니다. Suspense 밖의 캐시되지 않은 데이터 접근이 **빌드 에러**가 되므로,
> 모델 자체를 받아들일 준비가 됐을 때 켠다.

## use cache

```tsx
import { cacheLife, cacheTag } from 'next/cache'

// 데이터 단위
export async function getUsers() {
  'use cache'
  cacheLife('hours')
  return db.query('SELECT * FROM users')
}

// UI 단위 — 컴포넌트·페이지·레이아웃 전체
export default async function Page() {
  'use cache'
  cacheLife('hours')
  cacheTag('posts')
  // ...
}
```

- **모든 `use cache`에 `cacheLife`를 짝지어 쓴다.** 생략하면 암묵적 `default` 프로파일이 적용된다.
- 인자와 상위 스코프에서 캡처한 값이 **캐시 키**가 된다 — 입력이 다르면 별도 엔트리다.
- 파일 최상단에 쓰면 그 파일의 모든 export가 캐시된다.
- 기본 저장소는 인스턴스별 인메모리라 서버리스에서 휘발한다. 인스턴스 간 공유가 필요하면 `use cache: remote`
  (네트워크 왕복이므로 **적중률이 높을 때만** 이득).
- 배포가 바뀌면 캐시 키에 빌드 id가 포함돼 있어 `remote`조차 승계되지 않는다.

**무효화:** 지연 반영이 괜찮으면 `revalidateTag(tag, 'max')`, 사용자가 자기 변경을 즉시 봐야 하면
Server Action에서 `updateTag(tag)`, 클라이언트 라우터만 갱신하면 되면 `refresh()`.

## 런타임 API 다루기

`cookies`·`headers`·`searchParams`·`params`는 요청 시점에만 알 수 있다 — 접근하는 컴포넌트를 `<Suspense>`로 감싼다.

런타임 값을 캐시 함수의 **인자로 넘기면** 그 값이 캐시 키가 된다.

```tsx
async function ProfileContent() {                 // 캐시 안 됨 — 런타임 값을 읽는다
  const session = (await cookies()).get('session')?.value
  return <CachedContent sessionId={session} />
}

async function CachedContent({ sessionId }: { sessionId: string }) {
  'use cache'                                      // sessionId가 캐시 키
  return <div>{await fetchUserData(sessionId)}</div>
}
```

쿠키·헤더를 직접 읽는 함수에 수명을 주려면 `use cache: private` — 결과가 브라우저에만 저장된다.

`Math.random()`·`Date.now()`·`crypto.randomUUID()`는 명시적으로 다뤄야 한다.
요청마다 달라야 하면 `connection()`을 먼저 호출하고 `<Suspense>`로 감싸고, 모두가 같은 값을 봐도 되면 `use cache`로 감싼다.

## 정적 셸 극대화

**async 작업이 트리 아래로 내려갈수록 더 많은 부분이 정적으로 미리 렌더된다.** PPR 여부와 무관하게 유효한 구조 원칙이다.

```tsx
// ❌ layout 최상단에서 await — 레이아웃 전체가 프리렌더 불가
export default async function Layout({ children, params }) {
  const { slug } = await params
  return <div><Sidebar />{slug}{children}</div>
}

// ✅ Promise를 내려보내고 경계 안에서 await — Sidebar와 children이 정적 셸에 들어간다
export default function Layout({ children, params }) {
  return (
    <div>
      <Sidebar />
      <Suspense fallback={<h1>Loading...</h1>}>
        {params.then(({ slug }) => <SlugHeading slug={slug} />)}
      </Suspense>
      {children}
    </div>
  )
}
```

`cookies()`·`headers()`·`searchParams`·데이터 패칭 모두 같은 원칙이 적용된다.

**봇·크롤러 주의:** 크롤러에는 셸을 재사용하지 않고 요청 시점에 전체를 렌더한다. 셸이 빌드 타임에만
존재하는 값에 의존하면 사람에게는 열리는 페이지가 크롤러에게는 실패할 수 있다.
