# Postgres 직접 연결 (Prisma·Drizzle·psql 등)

> `supabase-guide` 스킬의 참조 문서. Postgres 드라이버로 DB에 직접 붙을 때만 읽는다.
> `supabase-js`는 PostgREST(HTTP)를 쓰므로 해당 없다.

| 환경 | 연결 | 주의 |
|------|------|------|
| 장기 실행 서버·컨테이너 | Direct (5432) | IPv6 필요 |
| 서버리스·Edge Function | Supavisor **transaction** (6543) | prepared statement **비활성 필수**, 인스턴스당 pool size 1 |
| BI·GUI 도구, IPv4 전용 | Supavisor **session** (5432) | prepared statement 지원 |

서버리스에서는 드라이버 클라이언트를 핸들러 안이 아니라 **모듈 스코프**에서 만든다 — 웜 인스턴스마다 커넥션이 쌓이는 것을 막는다.

---

## 커넥션 고갈 징후

- `remaining connection slots are reserved` / `too many clients already` → pool size 또는 인스턴스 수 과다.
- 서버리스에서 transaction 모드인데 `prepared statement "s1" already exists` → 드라이버에서 prepared statement 비활성화(`?pgbouncer=true`, `prepare: false` 등)가 빠진 것이다.
