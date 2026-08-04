# copernicus-web

**The core monorepo of the CopernicusAI Knowledge Engine.** It holds the Knowledge
Engine backend, the Next.js frontend, the suite's governance documents, and the
static assets behind several of the science-suite Hugging Face Spaces.

The name is historical: this began as a website and grew into the umbrella's
infrastructure. Governance for the whole suite lives in [`governance/`](governance/)
and is the record of truth for every project that inherits from the engine.

**Copyright (c) 2025–2026 Gary Welz / CopernicusAI**
**Licensed under the MIT License** — see [LICENSE](LICENSE).

## What's in here

| Path | What it is |
|---|---|
| `governance/` | Canonical suite governance — Constitution, Methods Catalog, Resource Pointer Manifest, Suite Reorganization Plan. Fetch these live; uploaded copies go stale. |
| `cloud-run-backend/` | The Knowledge Engine backend (FastAPI on Cloud Run): retrieval, research pipeline, podcast generation, content endpoints. Not a separate repo — no nested `.git` or submodule. |
| `app/`, `components/`, `lib/`, `api/` | Next.js 14 frontend — podcast episode browser, knowledge-engine views, dashboard, create flow. |
| `huggingface-space/` | Static site for the `copernicusai` Space, plus the scripts that publish catalogs, status pages, and the discipline process databases. |
| `papers/`, `docs/` | Corpus metadata and planning documents. |
| `scripts/`, `tools/` | Operational and one-off tooling. |
| `nsf-proposal/`, `doe-proposal/` | Grant proposal drafts. |
| `tda-analysis/`, `glmp-tda-analysis/` | Topological-data-analysis work over the GLMP flowchart corpus. |

Agent working rules, the repo↔Space map, and the suite's non-negotiables are in
[`CLAUDE.md`](CLAUDE.md).

## Related

- **Constitution** — [`governance/CONSTITUTION.md`](governance/CONSTITUTION.md)
- **Engines** — [glmp](https://github.com/garywelz/glmp) (biology) · [atap](https://github.com/garywelz/atap) (mathematics)
- **Methods & Tools** — [progframe](https://github.com/garywelz/progframe)
- **Live Space** — [huggingface.co/spaces/garywelz/copernicusai](https://huggingface.co/spaces/garywelz/copernicusai)

## Frontend setup

These steps cover the Next.js frontend only. The backend has its own setup in
[`cloud-run-backend/SETUP_DEPENDENCIES.md`](cloud-run-backend/SETUP_DEPENDENCIES.md).

1. Clone the repository:
```bash
git clone https://github.com/garywelz/copernicus-web.git
cd copernicus-web
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file with your Spotify credentials (see `.env.example`):
```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_SHOW_ID=your_show_id
```

4. Run the development server:
```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Environment variables

- `SPOTIFY_CLIENT_ID` — Spotify API client ID
- `SPOTIFY_CLIENT_SECRET` — Spotify API client secret
- `SPOTIFY_SHOW_ID` — Spotify podcast show ID

### Frontend tech stack

Next.js 14 · React 18 · TypeScript · Tailwind CSS · Spotify Web API
