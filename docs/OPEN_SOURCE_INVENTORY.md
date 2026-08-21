# Open-Source Frontend Inventory

**Scope:** direct dependencies declared by `apps/web-react/package.json`.  
**Runtime state:** source scaffold only; no lockfile or production bundle was generated in this environment.

| Package | Version | Purpose | License | URL | Approved |
|---|---:|---|---|---|---|
| @refinedev/core | 5.0.12 | resource/data framework | MIT | https://www.npmjs.com/package/@refinedev/core | yes |
| @refinedev/antd | 6.0.3 | Ant Design adapter | MIT | https://www.npmjs.com/package/@refinedev/antd | yes |
| @refinedev/react-router | 2.0.4 | routing adapter | MIT | https://www.npmjs.com/package/@refinedev/react-router | yes |
| antd | 6.5.3 | enterprise components | MIT | https://www.npmjs.com/package/antd | yes |
| @ant-design/icons | 6.3.2 | icon set | MIT | https://www.npmjs.com/package/@ant-design/icons | yes |
| react | 19.2.7 | UI runtime | MIT | https://www.npmjs.com/package/react | yes |
| react-dom | 19.2.8 | DOM renderer | MIT | https://www.npmjs.com/package/react-dom | yes |
| react-router-dom | 7.18.0 | browser routing | MIT | https://www.npmjs.com/package/react-router-dom | yes |
| @tanstack/react-query | 5.101.4 | async state | MIT | https://www.npmjs.com/package/@tanstack/react-query | yes |
| vite | 8.2.1 | build tool | MIT | https://www.npmjs.com/package/vite | yes |
| typescript | 5.8.3 | language/compiler | Apache-2.0 | https://www.npmjs.com/package/typescript | yes |
| vitest | 4.1.10 | unit test runner | MIT | https://www.npmjs.com/package/vitest | yes |

## Governance gates

1. Generate and commit a package lock in an approved network environment.
2. Produce a transitive license report and SBOM from that lockfile.
3. Reject copyleft/source-available/commercial-only packages unless separately approved.
4. Re-run typecheck, tests, production build and browser E2E before activating `/app-next/`.
