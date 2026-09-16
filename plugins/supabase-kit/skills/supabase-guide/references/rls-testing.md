# RLS 테스트 (pgTAP)

> `supabase-guide` 스킬의 참조 문서. RLS 정책을 실제로 검증하는 테스트를 작성할 때만 읽는다.

## 왜 별도 테스트가 필요한가

SQL Editor는 `postgres` 역할로, Admin Client는 Secret 키로 실행되므로 **둘 다 RLS를 우회한다.**
거기서 "잘 되더라"는 정책이 동작한다는 근거가 되지 못한다. 역할과 JWT 클레임을 주입해 검증해야 한다.

## 테스트 파일

`supabase/tests/<table>_rls.test.sql`에 두고 `supabase test db`로 실행한다.
(최초 생성은 `supabase test new resources_rls.test`)

```sql
-- supabase/tests/resources_rls.test.sql
begin;
select plan(3);

set local role authenticated;
set local request.jwt.claims to '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}';

-- 1) 타인 행이 보이지 않는다
select is_empty(
  $$ select id from resources where user_id <> '11111111-1111-1111-1111-111111111111' $$,
  '타인 리소스 미노출'
);

-- 2) 타인 소유로 INSERT 불가 — WITH CHECK 위반은 42501로 던진다
select throws_ok(
  $$ insert into resources (user_id) values ('22222222-2222-2222-2222-222222222222') $$,
  '42501', null, '타인 소유 생성 차단'
);

-- 3) USING이 걸러내는 UPDATE는 에러가 아니라 0행이다
select is_empty(
  $$ update resources set name = 'x'
     where user_id = '22222222-2222-2222-2222-222222222222' returning id $$,
  '타인 리소스 수정 0행'
);

select * from finish();
rollback;
```

## 어서션 선택 기준

| 차단 방식 | 결과 | 어서션 |
|-----------|------|--------|
| grant 없음 | 에러 `42501` | `throws_ok(..., '42501')` |
| `WITH CHECK` 위반 | 에러 `42501` | `throws_ok(..., '42501')` |
| `USING`이 행을 걸러냄 | 에러 없이 **0행** | `returning` + `is_empty` |

- **`lives_ok`로 쓰기를 검증하지 않는다** — 0행이 변경돼도 통과하므로 차단을 확인하지 못한다.
- `USING` 차단을 확인한 뒤에는 대상 행이 실제로 그대로인지도 함께 단언한다.

## 성능까지 같이 본다

```sql
set local role authenticated;
set local request.jwt.claims to '{"sub":"<uuid>","role":"authenticated"}';
explain analyze select count(*) from resources;
```

클라이언트에서 확인할 때:

```ts
const { data } = await supabase.from('resources').select('*').explain({ analyze: true })
// 사전에: alter role authenticator set pgrst.db_plan_enabled to true;
```

Seq Scan이 보이면 정책 컬럼 인덱스가 없거나 `auth.uid()` 래핑이 빠진 것이다.
