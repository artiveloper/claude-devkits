# Next.js 16 기준선과 마이그레이션

> `nextjs-guide` 스킬의 참조 문서. 15 → 16 업그레이드를 하거나, 코드가 어느 버전 기준인지 판단할 때만 읽는다.

## 목차
1. [업그레이드 절차](#업그레이드-절차)
2. [깨지는 변경](#깨지는-변경)
3. [제거된 것](#제거된-것)

## 업그레이드 절차

```bash
npx @next/codemod@canary upgrade latest              # 대부분의 기계적 변환
npx @next/codemod@canary next-async-request-api .    # 동기 params/cookies가 남아 있다면 추가로
```

코드모드가 처리하는 것: `next.config`의 turbopack 설정 이동, `next lint` → ESLint CLI, `middleware` → `proxy`,
안정화된 API의 `unstable_` 접두사 제거, `experimental_ppr` 세그먼트 설정 제거.

요구사항: Node.js 20.9+, TypeScript 5.1+, Chrome/Edge/Firefox 111+ · Safari 16.4+.

## 깨지는 변경

| 항목 | 변경 |
|------|------|
| Async Request API | `cookies`·`headers`·`draftMode`·`params`·`searchParams` **동기 접근 완전 제거**. 15의 호환 기간 종료 |
| Turbopack | `next dev`/`next build` **기본**. 커스텀 webpack 설정이 있으면 빌드가 실패한다 — `--webpack`으로 옵트아웃 |
| `middleware` → `proxy` | 파일·함수·설정 플래그 모두 리네임. **`edge` 런타임 미지원**(런타임은 `nodejs` 고정, 설정 불가) — edge가 필요하면 `middleware`를 유지한다 |
| Parallel Routes | 모든 슬롯에 `default.js` **필수**. 없으면 빌드 실패 → `notFound()` 호출하거나 `null` 반환 |
| `revalidateTag` | 두 번째 인자(`cacheLife` 프로파일) **필수**. 즉시 만료가 필요하면 Server Action에서 `updateTag` 사용 |
| PPR | `experimental.ppr`·`experimental_ppr` 제거 → `cacheComponents: true`로 옵트인 (동작이 15 canary와 다르다) |
| 이미지 생성 함수 | `opengraph-image`·`icon` 등의 `params`·`id`가 Promise |
| `next/image` | `minimumCacheTTL` 60초 → 4시간, `qualities` 기본 `[75]`, `imageSizes`에서 16 제거, 리다이렉트 최대 3회, 로컬 IP 최적화 차단 |
| 스크롤 | `scroll-behavior: smooth` 전역 설정을 더 이상 덮어쓰지 않는다 — 이전 동작을 원하면 `<html data-scroll-behavior="smooth">` |

## 제거된 것

- **`next lint`** — Biome 또는 ESLint를 직접 쓴다. `next build`는 더 이상 린트를 돌리지 않는다. `next.config`의 `eslint` 옵션도 제거.
- **`serverRuntimeConfig` / `publicRuntimeConfig`** — 환경변수를 쓴다. 빌드 타임 인라인이 아니라 런타임에 읽어야 하면 `process.env` 접근 전에 `connection()`을 호출한다.
- **AMP** — `next/amp`, `export const config = { amp: true }`, `amp` 설정 전부.
- **`experimental.dynamicIO` / `experimental.useCache`** — `cacheComponents`로 통합.
- `unstable_rootParams` → `next/root-params`.
- `next build` 출력의 `size`·`First Load JS` 지표 — RSC 구조에서 부정확해 제거됐다. Lighthouse 등으로 측정한다.

## 알아둘 동작 변화

- `next dev`와 `next build`가 출력 디렉터리를 분리해(`.next/dev`) 동시 실행이 가능하다. 같은 프로젝트에서 중복 실행은 락파일이 막는다.
- `next dev` 실행 시 config 파일이 한 번만 로드된다 — config에서 `process.argv.includes('dev')`가 이제 `false`다. `NODE_ENV`로 판별한다.
- 라우팅/프리페치가 개편돼 레이아웃 중복 다운로드가 사라지고 증분 프리페치가 된다. 요청 **수**는 늘고 총 전송량은 준다 — 코드 변경 불필요.
