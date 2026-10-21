# ProjectLens frontend

Small React, TypeScript, and Vite client foundation. The Vite dev server proxies `/api` to `http://localhost:8000`; set `VITE_API_BASE` to override the API prefix (default `/api/v1`).

```sh
npm install
npm run dev
npm run build
npm test
```

The API must be running separately. See the repository README for backend setup. Tests use Vitest, jsdom, and Testing Library.
