# Supabase 클라이언트 설정 (Next.js)

> `supabase-guide` 스킬의 참조 문서. 프로젝트에 Supabase 클라이언트를 처음 놓거나
> 기존 설정 파일을 손볼 때만 읽는다. 어떤 클라이언트를 언제 쓰는지 판단하는 기준은 SKILL.md 1절에 있다.

## 목차
1. [클라이언트 3종](#클라이언트-3종)
2. [토큰 갱신 (proxy.ts)](#토큰-갱신-proxyts)

설치: `@supabase/supabase-js` + `@supabase/ssr` (프로젝트가 쓰는 패키지 매니저로).

## 클라이언트 3종

### Browser Client (Client Component용)

```ts
// src/lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr'
import type { Database } from '@/types/database'

export function createClient() {
  return createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  )
}
```

### Server Client (Server Component / Server Action / Route Handler용)

```ts
// src/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import type { Database } from '@/types/database'

export async function createSupabaseServerClient() {
  const cookieStore = await cookies()
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {
            // Server Component에서는 쿠키 set 불가 — 무시
          }
        },
      },
    }
  )
}
```

`createBrowserClient`는 싱글턴이라 반복 호출해도 안전하지만, 서버 클라이언트는 **요청마다 새로 생성**한다
(모듈 스코프 캐싱 금지 — 다른 사용자의 세션이 섞인다).

### Admin Client (서버 전용 — RLS 우회)

```ts
// src/lib/supabase/admin.ts
import { createClient } from '@supabase/supabase-js'  // ← @supabase/ssr 아님
import type { Database } from '@/types/database'

export function createSupabaseAdminClient() {
  return createClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SECRET_KEY!,
    {
      auth: { autoRefreshToken: false, persistSession: false },
    }
  )
}
```

## 토큰 갱신 (proxy.ts)

렌더 계층은 쿠키를 쓸 수 없으므로 갱신은 요청 앞단의 책임이다(근거는 SKILL.md 2절).
Next.js 15 이하는 파일·함수명이 `middleware.ts` / `middleware`다.

```ts
// src/proxy.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function proxy(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll() },
        setAll(cookiesToSet) {
          // 요청·응답 양쪽에 써야 한다 — 한쪽만 쓰면 갱신 토큰이 유실된다
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  await supabase.auth.getClaims()   // 반드시 호출 — 토큰 갱신 트리거

  return supabaseResponse   // 반드시 이 응답을 반환 — 새 쿠키가 실려 있다
}
```

`matcher` 설정과 리다이렉트 로직은 Next.js 파일 컨벤션이다 — **nextjs-kit 설치 시** `nextjs-guide`를 참조하고,
미설치면 Next.js 공식 문서를 따른다.
