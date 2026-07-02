# VECNA

**V**ault **E**xtensible **C**omputational **N**exus for **A**dventurers

A Python **MCP server** for D&D 5e SRD data (monsters, spells, classes, dice),
plus a static browser frontend. Designed to be **hosted persistently**: the
server runs on Render, the frontend on GitHub Pages, and both redeploy
automatically on every push to `master`.

## What is this?

MCP = Model Context Protocol — an open standard that lets AI assistants (Claude,
OpenCode, etc.) call functions and read data from external tools.

VECNA exposes:
- **Tools** — functions the AI can call (`get_monster`, `roll_dice`, …)
- **Resources** — data the AI can read
- **Prompts** — templates the AI can load

It ships **two transports**:
- **stdio** (default) — for local AI clients that spawn the process.
- **Streamable HTTP** (`VECNA_TRANSPORT=http`) — exposes `POST/GET /mcp` for AI
  clients over the network, plus `GET /api/...` REST endpoints for the frontend.

## Architecture (hosted)

```
                 push to master
GitHub repo ──────────┬────────────────► Render  (Docker web service)
                      │                   https://vecna-svpo.onrender.com
                      │                     /mcp        ← AI clients (opencode, Claude)
                      │                     /api/...    ← REST for the frontend
                      │                     /api/health ← health check
                      │
                      └────────────────► GitHub Pages (static frontend)
                                          https://andreasmaurer0210.github.io/VECNA/
                                            fetches /api from the Render URL
```

- **Persistent** (req #2): the Render URL and the Pages URL are **stable** and
  survive restarts/redeploys. `render.yaml` + `autoDeploy` and the Pages
  workflow rebuild automatically on push, so a change redeploys to the *same*
  URL — reachable exactly like before.
- **Note on the Render free tier:** the service sleeps after ~15 min idle; the
  next request wakes it (~50 s cold start). The URL never changes.

---

## Local development

```bash
uv sync

# stdio transport (what local AI clients use)
uv run vecna

# HTTP transport (serves /mcp + /api on :8000, same as production)
VECNA_TRANSPORT=http VECNA_PORT=8000 uv run vecna
# health:  curl http://localhost:8000/api/health
# open frontend against it:  frontend/index.html?server=http://localhost:8000
```

---

## Deploy the server to Render

The repo already contains [`render.yaml`](render.yaml) (Blueprint) and a
[`Dockerfile`](Dockerfile).

**One-click** (reads `render.yaml`, just sign in to Render):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/andreasmaurer0210/VECNA)

Or manually:

1. Push the repo to GitHub (`git push origin master`).
2. Render dashboard → **New → Blueprint** → select the `VECNA` repo.
3. Render reads `render.yaml`, creates the **`vecna`** web service, and deploys.
4. When the build finishes you get a URL: `https://vecna-svpo.onrender.com`
   (if the name is taken, Render appends a suffix, e.g. `https://vecna-ab12.onrender.com`).

Verify:
```bash
curl https://vecna-svpo.onrender.com/api/health      # → {"status":"ok","server":"vecna"}
```
The MCP endpoint is `https://vecna-svpo.onrender.com/mcp/`.

**Every later `git push` to `master` redeploys to the same URL** (`autoDeploy: true`).

---

## Deploy the frontend to GitHub Pages

The repo contains [`.github/workflows/pages.yml`](.github/workflows/pages.yml).
One-time setup:

1. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Push to `master`. The workflow publishes `frontend/` to
   `https://andreasmaurer0210.github.io/VECNA/`.
3. Point the frontend at your server. Either:
   - edit the `<meta name="vecna-server">` value in
     [`frontend/index.html`](frontend/index.html) to your Render URL and push, **or**
   - open the Pages URL with an override: `…/VECNA/?server=https://vecna-ab12.onrender.com`.

CORS is already open (`GET *`), and the Render URL is HTTPS, so the HTTPS Pages
site can call it without mixed-content errors.

---

## Configure the MCP in your AI client

### OpenCode

Edit `~/.config/opencode/opencode.json`. **Hosted (recommended):**

```json
{
  "mcp": {
    "vecna": {
      "type": "remote",
      "url": "https://vecna-svpo.onrender.com/mcp/",
      "enabled": true
    }
  }
}
```

Local stdio (for development) instead:

```json
{
  "mcp": {
    "vecna": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/path/to/VECNA", "vecna"],
      "enabled": true
    }
  }
}
```

### Claude Desktop

Edit `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`).
Claude Desktop reaches a remote Streamable-HTTP server through the `mcp-remote`
bridge:

```json
{
  "mcpServers": {
    "vecna": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://vecna-svpo.onrender.com/mcp/"]
    }
  }
}
```

Local stdio instead:

```json
{
  "mcpServers": {
    "vecna": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/VECNA", "vecna"]
    }
  }
}
```

Restart the client after editing config.

---

## Requirements → how they're met

| # | Requirement | Mechanism |
|---|-------------|-----------|
| 1 | MCP reachable from opencode | Render `https://vecna-svpo.onrender.com/mcp`, `type: remote` in opencode config |
| 2 | Reachable after restart/change, like before | `render.yaml` + `autoDeploy` → stable URL survives redeploys; Pages workflow same |
| 3 | Frontend same restrictions | GitHub Pages (stable URL, auto-deploy on push) fetching the Render `/api` |
| 4 | README docs + client config | This file (deploy steps + opencode/Claude config above) |

---

## Project structure

```
VECNA/
├── Dockerfile                     # Container Render builds
├── render.yaml                    # Render Blueprint (web service, autoDeploy)
├── .github/workflows/pages.yml    # Deploy frontend/ to GitHub Pages
├── .devcontainer/devcontainer.json# Optional: Codespaces (ephemeral) dev
├── frontend/index.html            # Static compendium UI (GitHub Pages)
├── pyproject.toml                 # Python project + dependencies
├── uv.lock                        # Pinned deps (reproducible builds)
└── src/vecna/
    ├── __init__.py                # CLI entry point (main)
    ├── server.py                  # MCP wiring + stdio/http transports
    ├── api.py                     # HTTP client for dnd5eapi.co
    ├── tools.py                   # MCP tool definitions + handlers
    ├── resources.py               # MCP resource handlers
    └── prompts.py                 # MCP prompt templates
```

## Adding a new tool

1. Add a `types.Tool(...)` entry in `tools.get_tool_definitions()`.
2. Add an `if name == "your_tool":` branch in `tools.handle_call_tool()`.
3. Write the handler function.

## License

MIT
