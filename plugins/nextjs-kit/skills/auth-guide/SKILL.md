---
name: auth-guide
description: >
  Better Auth 서버 설정·클라이언트 hook·proxy 세션 확인·Server Action 인가 패턴 가이드 —
  betterAuth() 설정, createAuthClient(), app/api/auth 핸들러, proxy.ts 연동, Drizzle adapter.
  better-auth, betterAuth, 인증 설정, 세션, useSession, signIn, signOut, auth middleware,
  auth 테이블 스키마 작업 시 사용. Supabase Auth는 supabase-guide 소관. NextAuth/Auth.js는 다루지 않음.
---

# Better Auth — Next.js 설정·패턴

> proxy.ts 작동 원리·matcher → `nextjs-guide` 7절 참조
> DB 스키마(auth 테이블) + Drizzle 설정 → `drizzle-guide` 참조
> Supabase Auth를 쓰는 경우 → `supabase-guide` 참조 (**supabase-kit 미설치 시 건너뛴다**)

---

## 1. 서버 설정 (lib/auth/auth.ts)

```ts
import 'server-only'
import { betterAuth } from 'better-auth'
import { drizzleAdapter } from 'better-auth/adapters/drizzle'
import { db } from '@/lib/db'

export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: 'pg',   // SQLite 사용 시 'sqlite'
  }),
  emailAndPassword: { enabled: true },
  // 소셜 로그인 추가 시:
  // socialProviders: { google: { clientId: process.env.GOOGLE_CLIENT_ID!, ... } }
})

export type Session = typeof auth.$Infer.Session
```

---

## 2. 클라이언트 (lib/auth/auth-client.ts)

```ts
import { createAuthClient } from 'better-auth/react'

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL,
})

export const { signIn, signUp, signOut, useSession } = authClient
```

클라이언트 컴포넌트에서:

```tsx
'use client'
import { useSession, signOut } from '@/lib/auth/auth-client'

export function UserMenu() {
  const { data: session } = useSession()
  if (!session) return null
  return (
    <button onClick={() => signOut()}>
      {session.user.email} 로그아웃
    </button>
  )
}
```

---

## 3. Route Handler (app/api/auth/[...all]/route.ts)

```ts
import { auth } from '@/lib/auth/auth'
export const { GET, POST } = auth.handler
```

---

## 4. proxy.ts 연동

```ts
// src/proxy.ts
import { NextResponse, type NextRequest } from 'next/server'
import { auth } from '@/lib/auth/auth'

export async function proxy(request: NextRequest) {
  const session = await auth.api.getSession({ headers: request.headers })

  const isAuthPage = request.nextUrl.pathname.startsWith('/login') ||
                     request.nextUrl.pathname.startsWith('/register')

  if (isAuthPage && session) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }
  if (!isAuthPage && !session) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  return NextResponse.next()
}

export const config = {
  // /api/auth/* 는 반드시 제외 — auth 핸들러가 동작해야 한다
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
```

**proxy에서 인가 끝냈다고 믿지 않는다.** Server Action은 `/api/` 경로 외부에서 직접 POST될 수 있으므로, proxy의 matcher에서 빠진 경로는 보호가 사라진다. Server Action마다 반드시 재인가한다 (→ `nextjs-guide` 5절).

---

## 5. Server Action 인가 패턴

```ts
'use server'
import { auth } from '@/lib/auth/auth'
import { headers } from 'next/headers'

export async function protectedAction(input: unknown) {
  const session = await auth.api.getSession({ headers: await headers() })
  if (!session) throw new Error('Unauthorized')

  // 소유권(IDOR) 검증 — proxy 통과 여부와 무관하게 확인
  // const resource = await db.query.resources.findFirst(...)
  // if (resource.ownerId !== session.user.id) throw new Error('Forbidden')
}
```

---

## 6. auth 테이블 스키마 (Drizzle)

Better Auth가 사용하는 테이블을 `lib/db/schema.ts`에 추가한다 (→ `drizzle-guide` 참조):

```ts
// PostgreSQL
import { pgTable, serial, text, boolean, timestamp } from 'drizzle-orm/pg-core'

export const users = pgTable('users', {
  id: text('id').primaryKey(),
  name: text('name'),
  email: text('email').unique().notNull(),
  emailVerified: boolean('email_verified').default(false),
  image: text('image'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
})

export const sessions = pgTable('sessions', {
  id: text('id').primaryKey(),
  userId: text('user_id').references(() => users.id, { onDelete: 'cascade' }).notNull(),
  token: text('token').unique().notNull(),
  expiresAt: timestamp('expires_at').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

export const accounts = pgTable('accounts', {
  id: text('id').primaryKey(),
  userId: text('user_id').references(() => users.id, { onDelete: 'cascade' }).notNull(),
  accountId: text('account_id').notNull(),
  providerId: text('provider_id').notNull(),
  accessToken: text('access_token'),
  refreshToken: text('refresh_token'),
  expiresAt: timestamp('expires_at'),
  password: text('password'),
})

export const verificationTokens = pgTable('verification_tokens', {
  id: text('id').primaryKey(),
  identifier: text('identifier').notNull(),
  value: text('value').unique().notNull(),
  expiresAt: timestamp('expires_at').notNull(),
})
```

스키마 추가 후 `npx drizzle-kit generate && npx drizzle-kit push` (→ `drizzle-guide` 5절).

---

## 7. 환경변수

```env
BETTER_AUTH_SECRET="최소-32자-랜덤-문자열"   # openssl rand -base64 32
BETTER_AUTH_URL="http://localhost:3000"
NEXT_PUBLIC_APP_URL="http://localhost:3000"
```

---

## Gotchas (운영하며 축적)

- `BETTER_AUTH_SECRET`은 최소 32자 랜덤 문자열이어야 한다 — 짧으면 런타임 에러 발생. `openssl rand -base64 32`로 생성한다.
- proxy의 matcher에서 `/api/auth` 경로를 제외하지 않으면 auth 핸들러 요청도 세션 미확인으로 redirect된다. `/((?!api|...).*)`로 `/api` 전체를 제외하는 것이 가장 안전하다.
- `createAuthClient`의 `baseURL`을 하드코딩하면 배포 환경에서 콜백 URL이 틀어진다 — `NEXT_PUBLIC_APP_URL` 환경변수로 분기한다.
- proxy에서 세션을 확인했더라도 Server Action이 다른 matcher 범위 밖 경로로 POST되면 보호가 사라진다 — Server Action마다 `auth.api.getSession()`을 반드시 재호출한다.
- `auth.handler`를 `[...all]` 대신 다른 경로에 두면 `createAuthClient`의 기본 경로(`/api/auth`)와 어긋난다 — `basePath` 옵션으로 맞춰야 한다.

> 운영 중 새로 발견한 함정은 이 섹션에 계속 축적한다.
