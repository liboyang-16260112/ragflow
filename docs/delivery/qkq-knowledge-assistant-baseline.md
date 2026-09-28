# QKQ Knowledge Assistant RAGFlow Baseline

- Baseline branch: `dev_gsjz_0.1`
- Baseline commit: `acf06cdf5dcb169b7624f724f625a6db821ebb7c`
- Feature branch: `codex/deliver-gsjz-knowledge-assistant`
- Recorded on: `2026-09-20`
- RAGFlow delivery baseline: `0.27.2`

The feature branch was created from a clean `dev_gsjz_0.1` working tree. Production
0.26.4 application data is not an implementation or migration input for this branch.

## Web delivery hotfix (2026-09-22)

- Active image: `ragflow:0.27.2-gsjz-20260922.3`
- Image ID: `sha256:228e300e18aa368bd9ac5eda22de9cbcd339087284bd73aac19ec46a11e57c50`
- Web artifact: `ragflow-web-0.27.2-gsjz-20260922.3-api-prefix-zh-nav.tar.gz`
- Artifact SHA-256: `d4ff84d690193e606c1e001e916de1b66609f646352fd7b77da7c8c3049b00ce`
- Built index SHA-256: `a8e01bd9dd0de7c0ff200c4d1f049dc7a133253cd92d4e83b4731665a3b0af98`
- Browser base: `/ragflow/`
- API base: `/ragflow-api/`
- Embedded default language: Simplified Chinese (`zh`)
- Embedded native navigation hides Chat, Search, Agent and Memory while retaining dataset/knowledge-management functions.
- The deployment rebuilt only the 0.27.2 application image. It did not migrate or modify the 0.26.4 business data or the dedicated 0.27.2 database/storage namespaces.
- Targeted web tests: 3 suites / 17 tests passed. The production web build succeeded. Repository-wide Jest and TypeScript checks retain unrelated pre-existing baseline failures and are not recorded as passing.

## Production cutover (2026-09-22)

- Production container: `fmoss-rag-server-cpu`
- Active image: `ragflow:0.27.2-gsjz-20260922.4`
- Host ports: Web/HTTPS `280/2443`; API/Admin/MCP/Go `9380-9384`
- Shared RAGFlow tenant account: `zqykj@zqykj.com`; QKQ users continue to authenticate with their individual QKQ accounts, and the browser is not given the shared RAGFlow credential.
- The former 0.26.4 application container and the 0.27.2 rehearsal container were removed by the site decision. The old `fmoss-ragflow:local` image, old configuration and original logical data remain available for an explicit rollback recreation.
- The 172.30.6.66 RAGFlow UI/API upstream now targets port `280`.
- QKQ knowledge-question settings now load the shared tenant datasets and persist a multi-select knowledge scope through the managed Chat `dataset_ids`; an empty selection remains valid for general chat.
- The deployed dataset contract uses a direct array response and `chunk_count`; the QKQ adapter accepts that contract and retains `chunk_num` as a compatibility fallback.

## Embedded Chinese and return navigation hotfix (2026-09-22)

- Active image: `ragflow:0.27.2-gsjz-20260922.4`
- Image ID: `sha256:41d6ac5c99c730b5301f9bf1575a1b0156d7055d15d3fb8c4095c120fc09c211`
- Web artifact: `ragflow-web-0.27.2-gsjz-20260922.4-zh-return.tar.gz`
- Artifact SHA-256: `e0c05d5b7ca3c599ccd49af3209d861b3dbce36858aad67b373220dc6ddfa360`
- Built index SHA-256: `65cad3c5b83dabac6232089d40c3ba3ee5e00f6830a4a8540a01cc06f2791f2e`
- Embedded delivery normalizes both initial and requested languages to Simplified Chinese, so stale English browser storage cannot switch the dataset-management UI back to English.
- Desktop and mobile embedded navigation expose a root-relative `返回知识问答` action to `/workspace/knowledge`; standalone RAGFlow does not render it.
- Targeted Web tests: 4 suites / 20 tests passed; changed-file oxlint and the production Web build passed. Repository-wide TypeScript checks retain unrelated pre-existing failures.

## Locale alias and top-level return navigation hotfix (2026-09-23)

- Active image: `ragflow:0.27.2-gsjz-20260923.5`
- Image ID: `sha256:2ac1540b185437b391120da61497ba1b72622d1eeb168f0a443474a62bb608ed`
- Web artifact: `ragflow-web-0.27.2-gsjz-20260923.5-zh-logo-return.tar.gz`
- Artifact SHA-256: `f56b7cd93ca0daf996631c0b56b5539fd2296f8a9a73ffd7571e2c228484775e`
- Built index SHA-256: `09ca3d5520042da200c6ce4c2419c4e6b6d572fc711cc1b83623cf32aa0336f7`
- The production alias `zh` is normalized to `zh-Hans`; embedded language switching is hidden and stale English browser storage cannot force an English fallback.
- The centered return button is removed. The upper-left `size-10` brand control targets `_top` and navigates to the QKQ Hash route `/#/workspace/knowledge`.
- Targeted Web tests: 5 suites / 22 tests passed; changed-file oxlint and the production Web build passed.
- Production verification used an authenticated QKQ browser session with an English local preference: `/ragflow/datasets` rendered Chinese labels and the logo returned to the authenticated knowledge workspace.

## Reusable field deployment configuration (2026-09-28)

- The former `*rehearsal*` Compose and full-copy environment files were one-time cutover artifacts and are not the supported future deployment entry.
- Generic defaults remain in `docker/.env`; QKQ integration defaults are disabled/empty there so ordinary RAGFlow deployments are unchanged.
- `docker/.env.gsjz-field.example` is the sanitized minimal override template. The real `docker/.env.gsjz-field` is ignored and must hold field credentials locally.
- `docker/docker-compose-qkq-field.yml` starts only `fmoss-rag-server-cpu`, disables duplicate unprofiled MinIO/Redis services, and connects to the external `dev` network.
- `docker/README-gsjz-field.md` is the maintained render, deploy, verify and rollback runbook.
