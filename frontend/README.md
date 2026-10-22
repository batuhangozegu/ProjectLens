# ProjectLens frontend

Small React, TypeScript, and Vite client foundation. The Vite dev server proxies `/api` to `http://localhost:8000`; set `VITE_API_BASE` to override the API prefix (default `/api/v1`).

```sh
npm install
npm run dev
npm run build
npm test
```

The API must be running separately. See the repository README for backend setup. Tests use Vitest, jsdom, and Testing Library.

## Using the app

Start the API (see the repository README), then run `npm run dev` and open the printed local URL (usually http://localhost:5173).

1. On **Your projects**, paste a public GitHub repository URL (`https://github.com/owner/repository`) and choose **Add project**. Analysis runs in the background; the list updates when it finishes.
2. Open a project to see the **Overview**, then use the project navigation to switch views:
   - **Files**: collapsible file tree, dependency graph (cycle members highlighted) and a details panel. The tree is the keyboard-accessible alternative to the graph, which shows at most 120 files.
   - **Insights**: metrics, health score components, ranked risks and Git activity. These are static heuristics, not defect predictions; unavailable data is labelled as such.
   - **Roadmap**: manual progress from imported `TODO.md` tasks next to code-aware assessments. Import tasks through the API (see the repository README); status changes are saved immediately.
   - **AI**: optional. Nothing is sent until you request an explanation, and results are advisory. It requires an AI provider to be configured on the server.

Navigation uses URL hashes (`#/projects/1/files`), so the app works from any static file server. Set `VITE_API_BASE` at build time if the API is not served under `/api/v1`.

## Screenshots

Captured from a real analysis of a public repository (dark theme follows the system preference).

| Files and dependencies | Insights |
| --- | --- |
| ![Files](../docs/screenshots/projects-1-files.png) | ![Insights](../docs/screenshots/projects-1-insights.png) |
| **Roadmap** | **AI (optional)** |
| ![Roadmap](../docs/screenshots/projects-1-roadmap.png) | ![AI](../docs/screenshots/projects-1-ai.png) |

Project list and overview: [list](../docs/screenshots/projects.png), [overview](../docs/screenshots/projects-1.png).
