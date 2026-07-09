# VECNA

**V**ault **E**xtensible **C**omputational **N**exus for **A**dventurers

A Python **MCP server** for D&D 5e SRD data (monsters, spells, classes, dice),
plus a static browser frontend. Designed to run either locally or hosted: the
server can run through stdio or HTTP, the frontend can point at local or remote
HTTP, and the hosted deployment uses Render + GitHub Pages.

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

## Capabilities

Data source: the [D&D 5e SRD API](https://www.dnd5eapi.co) (`/api/2014`).
The server advertises **9 tools**, **2 resource families**, and **1 prompt**.

### Tools

| Tool | Args | Returns |
|------|------|---------|
| `list_monsters` | — | All 334 SRD monsters (`index` + name) |
| `search_monsters` | `query` | Monsters whose name matches the keyword |
| `get_monster` | `index` | Stat block: AC, HP, abilities, CR, senses, special abilities |
| `list_spells` | — | All 319 SRD spells (`index`, name, level) |
| `search_spells` | `query` | Spells whose name matches the keyword |
| `get_spell` | `index` | School, components, duration, damage, higher-level scaling |
| `list_classes` | — | All 12 classes |
| `get_class` | `index` | Hit die, saving throws, proficiencies, subclasses |
| `roll_dice` | `dice_expr` | Rolls `NdN(±mod)`, e.g. `2d6+3`, `1d20+5` |

### Resources

Read-only JSON under the `dnd://` scheme (listing caps at the first 50 of each):

| URI | Content |
|-----|---------|
| `dnd://monsters/{index}` | Raw monster JSON |
| `dnd://spells/{index}` | Raw spell JSON |

### Prompts

| Prompt | Args | Purpose |
|--------|------|---------|
| `create_character` | `class_name` (optional) | Guided level-1 character creation |

## Architecture sketch

### Local MCP (`stdio`)

The agent starts VECNA as a child process. MCP messages move over stdin/stdout;
no HTTP port is needed.

```
AI agent / client
  │
  │ MCP over stdio
  ▼
local `uv run vecna`
  │
  │ HTTPS reads
  ▼
public D&D 5e SRD API
https://www.dnd5eapi.co/api/2014
```

### Remote MCP (Streamable HTTP)

The agent connects to the hosted `/mcp/` endpoint. The browser frontend uses the
public REST API under `/api/...`; both are served by the same VECNA process.

```
AI agent / client ───── MCP HTTP ─────► https://vecna-svpo.onrender.com/mcp/
                                             │
Browser frontend ───── REST JSON ─────► https://vecna-svpo.onrender.com/api/...
                                             │
                                             │ HTTPS reads
                                             ▼
                                   public D&D 5e SRD API
                                   https://www.dnd5eapi.co/api/2014
```

### Hosted deployment

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
cp .env.example .env

# stdio transport (what local AI clients use)
uv run vecna

# HTTP transport (serves /mcp + /api on :8000, same as production)
VECNA_TRANSPORT=http VECNA_PORT=8000 uv run vecna
# health:  curl http://localhost:8000/api/health
```

To run the frontend against the local server:

```bash
python3 -m http.server 8080 --directory frontend
# open http://localhost:8080/?server=http://localhost:8000
```

---

## Hosting configuration

Server runtime is configured by environment variables:

| Variable | Local value | Hosted value | Purpose |
|----------|-------------|--------------|---------|
| `VECNA_TRANSPORT` | `http` or unset for stdio | `http` | Selects stdio vs Streamable HTTP |
| `VECNA_HOST` | `127.0.0.1` | unset (`0.0.0.0` default) | Bind address |
| `VECNA_PORT` | `8000` | unset | Local HTTP port |
| `PORT` | unset | Render-provided | Hosted HTTP port |

Frontend server URL is configured in this order:

1. `?server=...` query string override.
2. `frontend/config.json` (committed default, currently Render).
3. Embedded fallback `<meta name="vecna-server">`.

Remote default:

```json
{
  "server": "https://vecna-svpo.onrender.com"
}
```

Local override uses the query string, e.g. `?server=http://localhost:8000`.

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
   - edit [`frontend/config.json`](frontend/config.json) to your Render URL and push, **or**
   - open the Pages URL with an override: `…/VECNA/?server=https://vecna-ab12.onrender.com`.

CORS is already open (`GET *`), and the Render URL is HTTPS, so the HTTPS Pages
site can call it without mixed-content errors.

---

## Configure the MCP in your AI client

MCP connection mode is configured in the AI client, not in the frontend.

| Client | Config file | Local MCP | Remote MCP |
|--------|-------------|-----------|------------|
| OpenCode | `~/.config/opencode/opencode.json` | `type: "local"` + `command` | `type: "remote"` + `url` |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` | `command: "uv"` | `command: "npx"` + `mcp-remote` |

Server runtime mode is configured in the server environment:

| Runtime | Config location | Value |
|---------|-----------------|-------|
| Local stdio MCP | unset env vars | default `VECNA_TRANSPORT=stdio` |
| Local HTTP MCP/API | shell or `.env.example` copy | `VECNA_TRANSPORT=http`, `VECNA_PORT=8000` |
| Hosted HTTP MCP/API | [`render.yaml`](render.yaml) | `VECNA_TRANSPORT=http`; Render injects `PORT` |

Frontend public API URL is configured separately in [`frontend/config.json`](frontend/config.json)
or with `?server=...`. That affects browser REST calls only, not MCP client mode.

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
├── .env.example                   # Local HTTP server env template
├── Dockerfile                     # Container Render builds
├── render.yaml                    # Render Blueprint (web service, autoDeploy)
├── .github/workflows/pages.yml    # Deploy frontend/ to GitHub Pages
├── .devcontainer/devcontainer.json# Optional: Codespaces (ephemeral) dev
├── frontend/index.html            # Static compendium UI (GitHub Pages)
├── frontend/config.json           # Committed remote frontend server URL
├── frontend/js/                   # Frontend behavior modules
├── frontend/styles/               # Frontend CSS modules
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
2. Write the `_handle_your_tool(...)` handler function.
3. Add it to the `handlers` map in `tools.handle_call_tool()`.

## License

MIT
