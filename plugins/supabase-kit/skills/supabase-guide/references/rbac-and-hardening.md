# RBAC와 Data API 하드닝

> `supabase-guide` 스킬의 참조 문서. 역할이 2개를 넘거나, `public` 스키마를 API에 노출하고 싶지 않을 때만 읽는다.
> 단일 `admin` 플래그 수준이면 `app_metadata.role`로 충분하다.

## 목차
1. [Custom Access Token Auth Hook 기반 RBAC](#custom-access-token-auth-hook-기반-rbac)
2. [전용 api 스키마로 Data API 축소](#전용-api-스키마로-data-api-축소)

## Custom Access Token Auth Hook 기반 RBAC

`app_metadata`는 사용자마다 값을 직접 박아 넣는 구조라 권한 체계가 커지면 관리가 무너진다.
역할·권한을 테이블로 두고, 토큰 발급 시점에 훅이 클레임을 주입한다.

```sql
-- 역할 ↔ 사용자, 역할 ↔ 권한
create table public.user_roles (
  user_id uuid references auth.users on delete cascade,
  role app_role not null,
  primary key (user_id, role)
);

create table public.role_permissions (
  role app_role not null,
  permission app_permission not null,
  primary key (role, permission)
);
```

훅이 넣은 `user_role` 클레임을 읽어 권한을 판정하는 함수를 만들고, 정책에서 호출한다.

```sql
create or replace function public.authorize(requested_permission app_permission)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  bind_permissions int;
  user_role public.app_role;
begin
  select (auth.jwt() -> 'app_metadata' ->> 'user_role')::public.app_role into user_role;

  select count(*) into bind_permissions
  from public.role_permissions
  where role_permissions.permission = requested_permission
    and role_permissions.role = user_role;

  return bind_permissions > 0;
end;
$$;

-- 정책에서: USING ((select public.authorize('resources.delete')))
```

주의할 점:

- 훅은 **access token JWT만** 수정한다. `session` 객체에는 커스텀 클레임이 없으므로 `getClaims()`로 토큰을 디코드해 읽는다.
- 역할을 바꿔도 **다음 토큰 갱신 전까지 반영되지 않는다** — 즉시 반영이 필요한 판정은 DB를 직접 조회한다.
- 훅 함수와 권한 테이블은 노출 스키마에 두지 않거나, 최소한 RLS로 잠근다.

## 전용 api 스키마로 Data API 축소

`public`을 그대로 노출하면 내부 테이블·감사 로그·헬퍼 함수까지 API 표면이 된다.
클라이언트가 접근해야 하는 객체만 `api` 스키마에 두고, Data API의 노출 스키마를 `api`로 바꾼다.

```sql
create schema if not exists api;
create schema if not exists private;   -- 내부 전용, 절대 노출하지 않음

grant usage on schema api to anon, authenticated;

-- 기본 grant가 자동으로 붙지 않도록 차단
alter default privileges in schema api revoke all on tables from anon, authenticated;

-- 필요한 것만 명시적으로
grant select on api.catalog_items to anon, authenticated;
grant select, insert, update, delete on api.resources to authenticated;
```

- 노출 스키마 설정은 대시보드 Settings > API 또는 `config.toml`의 `[api] schemas`에서 바꾼다.
- security definer 함수는 `private`에 둔다 — 노출 스키마에 있으면 생성자 권한으로 API 호출이 가능해진다.
- 스키마를 나눠도 **RLS는 여전히 각 테이블에 켠다.** grant는 "무엇을", RLS는 "어떤 행을" 담당한다.
