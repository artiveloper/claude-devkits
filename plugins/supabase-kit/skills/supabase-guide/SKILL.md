---
name: supabase-guide
description: >
  Next.js + Supabase 실무 가이드 — @supabase/ssr 클라이언트 3종(browser/server/admin),
  인증(getClaims/getUser/getSession 선택, app_metadata 인가, proxy·middleware 토큰 갱신),
  grant + RLS 2층 권한 모델·정책 성능, pgTAP RLS 테스트, publishable/secret 신규 API 키,
  타입 생성, 마이그레이션·선언적 스키마.
  Supabase, RLS, Row Level Security, @supabase/ssr, getClaims, publishable key, secret key,
  pgTAP, supabase db push 관련 작업 시 사용.
  DBMS 불문 스키마·인덱스 원칙(db-architecture), React Query 캐싱(react-query-guide),
  Next.js 파일 컨벤션(nextjs-guide)은 다루지 않는다.
---

# Supabase 가이드

> 원칙 1: DB는 항상 RLS로 보호한다. 클라이언트는 절대 신뢰하지 않는다.
> 원칙 2: 접근 권한은 **grant**(이 역할이 이 테이블에 무엇을 할 수 있는가)와 **RLS 정책**(그중 어떤 행인가)
> 두 층으로 결정된다. 한 층만 설정하면 보호되지 않는다.

---

## 1. 클라이언트 설정

세 가지 클라이언트를 구분해 쓴다. **섞으면 RLS가 뚫리거나 세션이 샌다.**

| 클라이언트 | 쓰는 곳 | 패키지 | 키 |
|-----------|--------|--------|-----|
| Browser | Client Component | `@supabase/ssr`의 `createBrowserClient` | Publishable |
| Server | Server Component / Server Action / Route Handler | `@supabase/ssr`의 `createServerClient` | Publishable |
| Admin (RLS 우회) | 서버 전용 관리 작업 | **`@supabase/supabase-js`의 `createClient`** | Secret |

- Admin 클라이언트만 `@supabase/ssr`이 아니다 — 세션·쿠키와 무관하게 동작해야 하므로 `autoRefreshToken`·`persistSession`을 끈다.
- `createBrowserClient`는 싱글턴이라 반복 호출해도 안전하지만, **서버 클라이언트는 요청마다 새로 생성**한다
  (모듈 스코프 캐싱 금지 — 다른 사용자의 세션이 섞인다).
- Server Component에서는 쿠키를 쓸 수 없어 `setAll`이 실패한다 — try/catch로 삼키고, 갱신은 2절에 맡긴다.

세 파일의 전체 코드(`client.ts`·`server.ts`·`admin.ts`)와 `proxy.ts` → `references/client-setup.md`.

---

## 2. 인증 패턴

### 토큰 검증 3종 — 무엇을 언제 쓰는가

| 메서드 | 검증 방식 | 비용 | 쓰는 곳 |
|--------|-----------|------|---------|
| `getClaims()` | JWT 서명을 **로컬 검증**(비대칭 서명 키 + JWKS 캐시) | 네트워크 없음 | **기본값** — 페이지·데이터 보호, 토큰 갱신 |
| `getUser()` | Auth 서버에 조회 | 매번 왕복 | 계정 정지·삭제가 **즉시** 반영돼야 하는 민감 작업 |
| `getSession()` | 저장소에서 그대로 읽음 (검증 없음) | 없음 | 클라이언트 UI 표시 전용 — **서버에서 사용 금지** |

```ts
// ✅ 기본 — 서명 검증된 클레임
const { data, error } = await supabase.auth.getClaims()
const userId = data?.claims.sub
if (!userId) return Response.json({ error: 'Unauthorized' }, { status: 401 })

// ✅ 즉시성이 필요할 때만 — 탈퇴/차단 반영
const { data: { user } } = await supabase.auth.getUser()

// ❌ 서버에서 신뢰 불가 — 쿠키는 위조될 수 있다
const { data: { session } } = await supabase.auth.getSession()
```

- 프로젝트가 아직 **대칭 서명 키**를 쓰면 `getClaims()`가 내부적으로 `getUser()`를 호출한다(네트워크 왕복 발생).
  대시보드에서 비대칭 JWT 서명 키로 전환해야 로컬 검증 이점이 생긴다.
- 클레임은 **토큰 발급 시점의 스냅샷**이다 — 권한을 회수해도 토큰이 갱신될 때까지 반영되지 않는다.

### JWT Claims — Role 확인

```ts
// ✅ app_metadata — 서버에서만 설정 가능, 신뢰 가능
const { data } = await supabase.auth.getClaims()
const role = data?.claims.app_metadata?.role  // 'admin' | undefined

// ❌ user_metadata — 사용자가 직접 수정 가능, 인가에 사용 금지
const role = data?.claims.user_metadata?.role
```

역할이 2개를 넘거나 권한을 세분화해야 하면 `app_metadata` 대신 Custom Access Token Auth Hook 기반
RBAC로 간다 → `references/rbac-and-hardening.md`.

### requireAdmin 헬퍼

```ts
// src/lib/supabase/server.ts
export async function requireAdmin() {
  const supabase = await createSupabaseServerClient()
  const { data } = await supabase.auth.getClaims()
  const claims = data?.claims
  if (!claims) throw new Error('Unauthorized')
  if (claims.app_metadata?.role !== 'admin') throw new Error('Forbidden')
  return { supabase, userId: claims.sub }
}
```

### 토큰 갱신 (`proxy.ts`)

`@supabase/ssr`은 세션을 쿠키에 담는다. **쿠키를 쓸 수 있는 계층에서만 토큰을 갱신할 수 있는데,
SSR 렌더 계층은 쿠키를 쓸 수 없다**(`server.ts`의 try/catch가 그 이유) — 그래서 갱신은 렌더 이전
계층의 책임이다. 누락하면 세션이 조용히 만료된다. 프레임워크 불문 원칙이다.

구현에서 틀리기 쉬운 세 가지 — 하나라도 빠지면 갱신이 조용히 실패한다.

1. `setAll`에서 **요청과 응답 양쪽에** 쿠키를 쓴다. 한쪽만 쓰면 갱신된 토큰이 유실된다.
2. **`getClaims()`를 반드시 호출**한다 — 이 호출이 갱신 트리거다.
3. 쿠키를 실어 만든 **그 응답 객체를 반환**한다. `NextResponse.next()`를 새로 만들어 반환하면 새 쿠키가 사라진다.

Next.js 구현 전체 코드(`proxy.ts`, 15 이하는 `middleware.ts`) → `references/client-setup.md`.

**여기서 인가를 끝내지 않는다.** 앞단 보호는 경로 매칭에 의존해 조용히 빠질 수 있다.
인가는 항상 Server Action·Route Handler 안에서 다시 확인하고, 최종 방어선은 RLS다.

---

## 3. API 키 관리

> 원칙: **레거시 `anon` / `service_role` (JWT) 키는 사용하지 않는다.**
> 항상 신규 **Publishable / Secret** 키를 사용한다. 레거시 키는 폐기 예정이다.

### 레거시 키 마이그레이션 → `references/key-migration.md`

레거시 `anon`/`service_role`(JWT) 키에서 신규 키로 교체할 때만 읽는다 — 키 비교표, 발급/교체 5단계 절차, 유출 대응 포함. 신규 프로젝트는 처음부터 Publishable/Secret 키만 쓰면 되므로 읽을 필요 없다.

### `anon` 키 vs `anon` 역할 — 혼동 주의

- **`anon` 키**(레거시 API 키) → 폐기 대상. `sb_publishable_...` 로 교체.
- **`anon` 역할**(Postgres role) → 그대로 존재. Publishable 키로 접근하되 로그인 세션이 없으면 여전히 `anon` 역할로 매핑된다.
- 따라서 키를 교체해도 RLS 정책의 `TO authenticated` / `TO anon` 구분은 그대로 유지된다.

### 환경변수

| 키 | 용도 | 노출 |
|----|------|------|
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Browser/SSR 클라이언트 | 공개 OK (RLS가 보호) |
| `SUPABASE_SECRET_KEY` | Admin 작업, RLS 우회 | 절대 클라이언트 노출 금지 |

```bash
# .env.local (git 제외)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxx
SUPABASE_SECRET_KEY=sb_secret_xxx

# ❌ 레거시(`eyJ...`) — 신규/기존 코드 모두에서 제거 대상
# NEXT_PUBLIC_SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY
```

- Secret 키는 여전히 RLS를 우회한다 → `NEXT_PUBLIC_` 접두사를 붙이는 순간 전 데이터가 공개된다. 절대 금지.
- 백엔드 컴포넌트(API 서버, Edge Function, 배치)마다 **별도 Secret 키**를 발급한다 — 유출 시 폐기 범위가 좁아진다.
- 로그에는 키를 남기지 않는다(불가피하면 앞 6자 또는 SHA256 해시만).
- Publishable 키는 공개돼도 안전하지만, 그 전제는 **모든 테이블에 RLS가 켜져 있다는 것**이다 (→ 4장).

---

## 4. RLS (Row Level Security)

> 노출 스키마의 모든 테이블에 RLS를 활성화한다. 예외 없음.

### 4.1 grant와 정책은 별개다

RLS를 켜도 `anon`/`authenticated`에 남아 있는 기본 grant는 사라지지 않는다. 최소 권한으로 다시 부여한다.

```sql
ALTER TABLE public.resources ENABLE ROW LEVEL SECURITY;
-- RLS 활성화 + 정책 없음 = 완전 차단 (안전한 기본값)

REVOKE ALL ON TABLE public.resources FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.resources TO authenticated;
-- 공개 읽기가 필요한 테이블만: GRANT SELECT ... TO anon;
```

내부 테이블·감사 로그를 Data API에 아예 노출하지 않으려면 전용 `api` 스키마로 분리한다
→ `references/rbac-and-hardening.md`.

### 4.2 정책 구조 원칙

| 작업 | USING | WITH CHECK |
|------|-------|------------|
| SELECT | ✅ | ❌ |
| INSERT | ❌ | ✅ |
| UPDATE | ✅ (기존 행) | ✅ (새 값) |
| DELETE | ✅ | ❌ |

- 작업별로 정책을 **따로** 만든다 — 하나의 `FOR` 절에 여러 작업을 넣을 수 없다.
- `TO authenticated`를 **항상 명시**한다. 생략하면 모든 역할에 대해 정책이 평가된다.
- `auth.uid()`는 비로그인 요청에서 `null`이고 `null = user_id`는 조용히 false가 된다 —
  `TO authenticated` 명시가 이 함정을 막는 1차 방어다.

### 4.3 성능 — `(select ...)` 래핑 + 인덱스

```sql
-- ❌ 모든 행마다 함수 실행 → 느림
USING (auth.uid() = user_id)

-- ✅ initPlan으로 한 번만 실행 후 캐시
USING ((select auth.uid()) = user_id)
```

```sql
-- 정책의 USING/WITH CHECK에 등장하는 컬럼은 반드시 인덱스
CREATE INDEX ix_resources_user_id ON resources (user_id);
CREATE INDEX ix_resource_logs_resource_id ON resource_logs (resource_id);
```

- 행마다 값이 달라지는 함수에는 래핑을 쓰지 않는다(결과가 캐시되어 틀린다).
- 정책이 보안을 책임지더라도 **클라이언트 쿼리에 같은 조건을 중복**으로 건다 —
  `.eq('user_id', userId)`가 있으면 플래너가 인덱스를 쓴다. RLS는 보안, 명시 필터는 성능이다.

### 4.4 RLS 패턴

**resources (소유자 기반 — 핵심):**
```sql
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_select_own_resources" ON resources
  FOR SELECT TO authenticated
  USING ((select auth.uid()) = user_id);

CREATE POLICY "users_insert_own_resources" ON resources
  FOR INSERT TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "users_update_own_resources" ON resources
  FOR UPDATE TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

CREATE POLICY "users_delete_own_resources" ON resources
  FOR DELETE TO authenticated
  USING ((select auth.uid()) = user_id);

-- admin: app_metadata.role 기반 (user_metadata 금지)
CREATE POLICY "admin_full_access_resources" ON resources
  FOR ALL TO authenticated
  USING ((select auth.jwt()->'app_metadata'->>'role') = 'admin');
```

**resource_logs (부모 소유자 기반) — 서브쿼리 방향이 성능을 가른다:**
```sql
-- ❌ 행마다 부모를 되짚는다
USING ((select auth.uid()) IN (SELECT user_id FROM resources WHERE id = resource_id))

-- ✅ 내 소유 목록을 먼저 만들고 대조한다
CREATE POLICY "users_own_resource_logs" ON resource_logs
  FOR SELECT TO authenticated
  USING (
    resource_id IN (
      SELECT id FROM resources WHERE user_id = (select auth.uid())
    )
  );
```

목록이 커지면 배열로 한 번에 평가시킨다 — `USING (resource_id = ANY(ARRAY(SELECT my_resource_ids())))`.

**공개 읽기:** `FOR SELECT TO anon, authenticated USING (is_active = true)` — 비로그인도 읽어야 하므로 `anon`을 포함한다.

**교집합이 필요할 때 — RESTRICTIVE:**
```sql
-- permissive 정책들은 OR로 결합된다. AND가 필요하면 restrictive를 쓴다.
CREATE POLICY "mfa_required_for_updates" ON resources
  AS RESTRICTIVE FOR UPDATE TO authenticated
  USING ((select auth.jwt()->>'aal') = 'aal2');
```

### 4.5 Security Definer 함수 (조인·복잡한 권한 체크)

정책 안에서 다른 테이블을 조인하면 그 테이블의 RLS까지 행마다 평가된다. 조인 로직을 함수로 감싼다.

```sql
CREATE OR REPLACE FUNCTION private.is_resource_owner(p_resource_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS(
    SELECT 1 FROM public.resources
    WHERE id = p_resource_id
      AND user_id = (SELECT auth.uid())
  );
$$;

-- 사용: USING ((select private.is_resource_owner(id)))
```

- `SET search_path = ''` + 모든 이름 스키마 한정은 **필수**다(권한 상승 방지).
- security definer 함수는 **노출 스키마에 두지 않는다** — Data API로 호출 가능해진다. `private` 스키마를 쓴다.

### 4.6 디버깅

| 증상 | 원인 | 조치 |
|------|------|------|
| `42501` (permission denied) | 정책이 아니라 **grant** 누락 | 4.1의 `GRANT` 확인 |
| `42P17` (infinite recursion) | 두 테이블 정책이 서로 참조 | security definer 함수로 순환 차단 |
| 조건에 맞는데 0행 | `auth.uid()`가 null이거나 `TO` 역할 불일치 | 로그인 세션·`TO authenticated` 확인 |
| UPDATE가 아무것도 안 바꿈 | SELECT 정책 부재 | UPDATE는 SELECT 정책을 함께 요구한다 |

```sql
-- RLS 꺼진 테이블 찾기 (배포 전 상시 점검)
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity = false;

SELECT * FROM pg_policies WHERE tablename = 'resources';   -- 정책 확인
```

---

## 5. RLS 테스트

> **SQL Editor(`postgres` 역할)와 Admin Client는 RLS를 우회한다.** 거기서 통과했다는 건 검증이 아니다.

- 정책 검증은 pgTAP 테스트를 `supabase/tests/<table>_rls.test.sql`에 두고 `supabase test db`로 돌린다.
- 역할·클레임 주입: `set local role authenticated;` + `set local request.jwt.claims to '{"sub":"<uuid>",...}';`
- **`lives_ok`로 쓰기를 검증하지 않는다** — 0행이 바뀌어도 통과해서 차단을 놓친다.
  grant·`WITH CHECK` 위반은 `throws_ok(..., '42501')`, `USING` 차단은 `returning` + `is_empty`로 확인한다.

테스트 파일 전체 예시·어서션 선택 기준·`explain analyze` 확인법 → `references/rls-testing.md`.

---

## 6. 타입 생성

```bash
supabase gen types typescript --local > src/types/database.ts                       # 로컬
supabase gen types typescript --project-id <id> > src/types/database.ts             # 원격
```

스키마 변경 시 반드시 재생성. CI에 타입 생성 + 커밋 체크 추가 권장.

---

## 7. 마이그레이션 & 스키마

```bash
supabase migration new add-resources-table   # 작성
supabase db reset                            # 로컬 전체 재적용 검증
supabase db push                             # 원격 적용
```

- **원격 DB를 대시보드/SQL Editor로 직접 고치지 않는다.** 마이그레이션 히스토리와 어긋나 이후 `db push`가 실패한다.
  이미 고쳤다면 `supabase db diff`로 차이를 마이그레이션 파일로 캡처한다.
- `db push`는 동시에 실행하지 않는다 — 타임스탬프 순 적용이라 충돌한다.
- `supabase/migrations/`는 git 커밋. 프로덕션 반영 전 staging(또는 Branching)에서 검증한다.

### 선언적 스키마 (선택)

테이블 정의를 `supabase/schemas/*.sql`에 최종 상태로 적어두고 `supabase db diff -f <name>`으로 마이그레이션을 생성한다.

- 비교 대상은 **스키마 파일 vs 마이그레이션 히스토리**다 — 라이브 DB 변경은 잡히지 않는다.
- diff가 놓치는 것(수동 마이그레이션으로 관리): DML, RLS 정책 `ALTER`, 뷰의 `security_invoker`·소유권, 머티리얼라이즈드 뷰, 파티션, COMMENT, publication.

Prisma·Drizzle·psql 등으로 Postgres에 **직접 연결**할 때의 Supavisor 모드·포트 선택과 서버리스 주의사항
→ `references/direct-connections.md` (`supabase-js`만 쓴다면 읽을 필요 없다).

---

## 8. 체크리스트

### 보안
- [ ] 노출 스키마 모든 테이블 RLS 활성화
- [ ] `REVOKE ALL` 후 최소 grant 재부여 (RLS만으로는 부족)
- [ ] SELECT/INSERT/UPDATE/DELETE 정책 각각 설정
- [ ] `TO authenticated` 명시 (null 비교 함정·anon 역할 차단)
- [ ] 뷰는 `with (security_invoker = true)`로 생성 (기본은 RLS 우회)
- [ ] security definer 함수는 `private` 스키마 + `SET search_path = ''`
- [ ] 레거시 `anon` / `service_role` (JWT) 키 미사용 → Publishable / Secret 키만 사용
- [ ] `SUPABASE_SECRET_KEY` 서버 전용, git 제외 (`NEXT_PUBLIC_` 접두사 금지)
- [ ] 교체 완료 후 대시보드에서 레거시 키 disable (자동 폐기되지 않음)
- [ ] `user_metadata`로 인가 처리 금지 → `app_metadata` 또는 auth hook 클레임 사용
- [ ] 서버에서 `getSession()` 사용 금지 → `getClaims()` (즉시성 필요 시 `getUser()`)
- [ ] Server Action·Route Handler 내부에서 인가 재확인 (앞단 갱신은 인가 수단이 아님)

### 성능
- [ ] 정책 컬럼 인덱스 추가 (user_id, resource_id 등)
- [ ] `auth.uid()` → `(select auth.uid())` 래핑
- [ ] 정책 내 조인은 security definer 함수로 분리
- [ ] 클라이언트 쿼리에 정책과 같은 필터 중복 명시

### 개발·운영
- [ ] 스키마 변경 시 타입 재생성
- [ ] `proxy.ts`(구 `middleware.ts`)에서 `getClaims()` 호출 (토큰 갱신)
- [ ] Admin Client는 `@supabase/supabase-js`의 `createClient` 사용 (`@supabase/ssr` 아님)
- [ ] RLS 정책마다 pgTAP 테스트 (`supabase test db`)
- [ ] 원격 DB 직접 수정 금지 — 모든 변경은 마이그레이션 경유
- [ ] 프로덕션: SSL Enforcement, Network Restrictions, PITR, OTP 만료 3600초 이하, 조직 MFA

---

## 9. Gotchas (운영하며 축적)

- RLS의 여러 permissive 정책은 **OR로 결합**된다 — admin `FOR ALL` 정책이 있으면 소유자 정책을 아무리 좁혀도 admin은 항상 통과한다. 교집합(AND)이 필요하면 `AS RESTRICTIVE` 정책을 쓴다.
- 토큰 갱신은 전적으로 요청 앞단(`proxy.ts`, 구 `middleware.ts`) 책임이다 — 경로 매칭에서 빠지면 그 경로의 세션이 조용히 만료된다. Supabase 쪽 증상은 "로그인했는데 Server Component에서만 로그아웃 상태"로 나타난다.
- `supabase gen types`가 생성하는 **뷰(view) 타입은 모든 컬럼이 nullable**이다 — 뷰 기반 조회는 non-null 보정(타입 가드/변환 함수)이 필요하다.
- **뷰는 기본적으로 RLS를 우회한다**(생성자 권한으로 실행). `create view v with (security_invoker = true) as ...`로 만들지 않으면 RLS를 다 걸어두고도 뷰로 전부 새어 나간다.
- `app_metadata`를 바꿔도 **토큰이 갱신될 때까지 반영되지 않는다** — 권한 강등은 즉시 반영되지 않으므로 중요한 경우 서버에서 DB를 직접 조회한다.
- Custom Access Token Auth Hook이 넣은 커스텀 클레임은 **access token에만** 들어간다 — `session` 객체에는 없으므로 토큰을 디코드(`getClaims()`)해서 읽는다.
- 마이그레이션에서 `CREATE TABLE`만 하고 `ENABLE ROW LEVEL SECURITY`를 빠뜨리면 그 테이블은 Data API로 전부 공개된다 — 테이블 생성과 RLS 활성화는 **같은 마이그레이션 파일**에 붙여 쓴다.

> 운영 중 새로 발견한 함정은 이 섹션에 계속 축적한다.
