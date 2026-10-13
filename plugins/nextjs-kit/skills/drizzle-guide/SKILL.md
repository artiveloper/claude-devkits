---
name: drizzle-guide
description: >
  Drizzle ORM 설정·스키마 정의·마이그레이션·쿼리 패턴 가이드 — lib/db/ 구조, PostgreSQL/SQLite 스키마,
  drizzle.config.ts, 마이그레이션 명령, Route Handler·Server Action에서 Drizzle 사용 패턴.
  drizzle, ORM, schema 정의, 마이그레이션, lib/db, drizzle-kit, DB 연결 설정, PostgreSQL/SQLite 스키마 작성
  작업 시 사용. Supabase DB는 supabase-guide 소관. Prisma는 다루지 않음.
---

# Drizzle ORM — Next.js 설정·패턴

> Next.js App Router + Server/Client 경계 → `nextjs-guide` 스킬 참조
> Server Action + ActionResult 패턴 → `react-query-guide` 스킬 참조
> Supabase DB를 쓰는 경우 → `supabase-guide` 스킬 참조 (**supabase-kit 미설치 시 건너뛴다**)

아래 예시의 테이블·도메인 이름(`todos` 등)은 자리표시자다 — 프로젝트의 실제 이름으로 바꿔 읽는다.

---

## 1. lib/db/ 구조

```
lib/db/
├── index.ts     — DB 클라이언트 싱글턴 (import 'server-only')
└── schema.ts    — 테이블 정의 + 타입 추론
```

- `import 'server-only'`를 `index.ts`에 붙여 클라이언트 번들로의 누출을 빌드 타임에 차단한다 (→ `nextjs-guide` 5절 DAL 원칙).
- `schema.ts`는 DB 모델만 — 비즈니스 로직·인가는 DAL 레이어에서 처리한다.

---

## 2. 스키마 정의

### PostgreSQL

```ts
// lib/db/schema.ts
import { pgTable, serial, text, boolean, timestamp } from 'drizzle-orm/pg-core'

export const todos = pgTable('todos', {
  id: serial('id').primaryKey(),
  title: text('title').notNull(),
  description: text('description'),
  completed: boolean('completed').default(false).notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
})

export type Todo = typeof todos.$inferSelect
export type NewTodo = typeof todos.$inferInsert
```

### SQLite (옵션)

```ts
import { sqliteTable, integer, text } from 'drizzle-orm/sqlite-core'

export const todos = sqliteTable('todos', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  title: text('title').notNull(),
  completed: integer('completed', { mode: 'boolean' }).default(false).notNull(),
  createdAt: integer('created_at', { mode: 'timestamp' })
    .notNull().$defaultFn(() => new Date()),
})

export type Todo = typeof todos.$inferSelect
export type NewTodo = typeof todos.$inferInsert
```

---

## 3. DB 클라이언트 (lib/db/index.ts)

### PostgreSQL

```ts
import 'server-only'
import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import * as schema from './schema'

const client = postgres(process.env.DATABASE_URL!, { prepare: false })
export const db = drizzle(client, { schema })
```

### SQLite

```ts
import 'server-only'
import { drizzle } from 'drizzle-orm/better-sqlite3'
import Database from 'better-sqlite3'
import * as schema from './schema'

const sqlite = new Database(process.cwd() + '/app.db')
export const db = drizzle(sqlite, { schema })
```

SQLite를 쓰면 `next.config.ts`에 다음을 추가한다:

```ts
const nextConfig = {
  serverExternalPackages: ['better-sqlite3'],
}
export default nextConfig
```

---

## 4. drizzle.config.ts

### PostgreSQL

```ts
import type { Config } from 'drizzle-kit'

export default {
  schema: './lib/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: { url: process.env.DATABASE_URL! },
} satisfies Config
```

### SQLite

```ts
export default {
  schema: './lib/db/schema.ts',
  out: './drizzle',
  dialect: 'sqlite',
  dbCredentials: { url: './app.db' },
} satisfies Config
```

---

## 5. 마이그레이션

```bash
npx drizzle-kit generate   # 마이그레이션 SQL 파일 생성 (drizzle/ 디렉터리)
npx drizzle-kit push       # DB에 직접 반영 (개발 환경 전용)
npx drizzle-kit studio     # 브라우저 GUI
```

- 프로덕션은 `generate`로 파일을 생성하고 그 파일을 커밋 → CI에서 마이그레이션을 실행한다. `push`는 스키마 변경 이력이 남지 않으므로 개발 전용이다.

---

## 6. Server Action에서 사용 패턴

```ts
// domain/todos/actions/todos.actions.ts
'use server'
import { db } from '@/lib/db'
import { todos } from '@/lib/db/schema'
import { eq } from 'drizzle-orm'

export async function getTodos() {
  return db.select().from(todos).orderBy(todos.createdAt)
}

export async function createTodo(input: NewTodo) {
  const [row] = await db.insert(todos).values(input).returning()
  return row
}

export async function deleteTodo(id: number) {
  await db.delete(todos).where(eq(todos.id, id))
}
```

- 인증·인가는 호출 전 DAL 레이어에서 확인한다 — `db.*`를 Server Action에서 직접 노출하지 않고 도메인 함수로 감싼다 (→ `nextjs-guide` 5절).
- ActionResult 봉투 패턴은 → `react-query-guide` 5절.

---

## 7. 환경변수

```env
DATABASE_URL="postgresql://user:pass@host:5432/mydb"
```

---

## Gotchas (운영하며 축적)

- Supabase Transaction pool mode(`:6543`)에서는 `prepare: false` 옵션이 필수다 — 없으면 prepared statement 에러 발생 (**supabase-kit 미설치 시 건너뛴다**).
- SQLite `better-sqlite3` 네이티브 바인딩 오류 시 `npm rebuild better-sqlite3` 실행. Node 버전이 바뀌거나 `node_modules`를 재설치할 때 발생하는 경우가 많다.
- `$inferSelect` / `$inferInsert`를 사용하지 않고 타입을 직접 정의하면 schema 변경 시 타입이 어긋난다 — Drizzle의 타입 추론을 그대로 쓴다.
- `push`는 개발 환경 전용이다 — 프로덕션 DB에 `push`하면 마이그레이션 이력이 남지 않아 롤백이 불가능하다.
- `drizzle-kit` CLI 버전과 `drizzle-orm` 버전은 반드시 맞춰야 한다 — 불일치 시 generate 단계에서 예상치 못한 diff가 나온다.

> 운영 중 새로 발견한 함정은 이 섹션에 계속 축적한다.
