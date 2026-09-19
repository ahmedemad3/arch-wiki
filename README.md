# arch-wiki 🏛️

> **Framework-agnostic architecture documentation skill** — Automatically sync your API modules, endpoints, Docker topology, SQL queries, permissions, and Swagger spec into a beautiful interactive HTML dashboard.

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/ahmedemad3/arch-wiki/releases)
[![Works with Antigravity](https://img.shields.io/badge/Antigravity-✓-blue)](#setup-in-antigravity)
[![Works with Claude Code](https://img.shields.io/badge/Claude_Code-✓-orange)](#setup-in-claude-code--cursor)
[![Works with Cursor](https://img.shields.io/badge/Cursor-✓-purple)](#setup-in-claude-code--cursor)
[![Works with Codex](https://img.shields.io/badge/Codex-✓-green)](#setup-in-openai-codex)
[![Works with OpenCode](https://img.shields.io/badge/OpenCode-✓-teal)](#setup-in-opencode)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-yellow)](https://python.org)

---

## What is arch-wiki?

Turn any backend codebase into an interactive architecture wiki that both developers and AI coding assistants can use.

`arch-wiki` is an AI skill (agent instruction set) that keeps your **living architecture documentation** in perfect sync with your codebase. Every time you add a module, endpoint, permission, SQL query, or Docker service — you invoke the skill, and it:

1. **Reads** your `architecture.json` manifest
2. **Scans** the changed source files
3. **Updates** the JSON manifest with new entries
4. **Regenerates** a fully interactive HTML dashboard

The output is a **single self-contained HTML file** with:
- 📊 Overview stats dashboard
- 📋 System Prerequisites & Setup Pipeline
- 📦 API Modules catalog with all endpoints & 1-click AI Analysis Prompts
- 🤖 Interactive Senior Developer Analysis Prompts modal for every API endpoint
- 🏗️ System Architecture diagram with pan/zoom & hand cursor (Mermaid)
- 🐋 Docker Topology diagram with pan/zoom & hand cursor (Mermaid)
- 📨 Async Messaging & Event Topology (Kafka, RabbitMQ, JMS, SQS)
- 📄 One-click PDF Export (exports all 11 sections into a single formatted PDF document)
- ⚡ Interactive Swagger UI (try-it-out enabled with polished dark mode theme)
- 🔐 Permissions & RBAC mapping (including SpEL object-level security)
- 🗃️ SQL & JPQL Queries catalog with syntax highlighting
- 🖥️ Infrastructure services catalog with environment-inferred edges
- 🛡️ Core Layer & Request Pipeline docs

---

## 🤖 AI Token & Context Optimization

Beyond serving as an interactive dashboard, `architecture.json` acts as a **machine-readable context index** specifically designed for AI coding assistants (Antigravity, Claude Code, Cursor, Codex, OpenCode, etc.):

- ⚡ **Fast Code Reading:** AI tools can read `docs/architecture/architecture.json` in a **single file view** to immediately understand all API modules, endpoints, database queries, RBAC permissions, and container topologies.
- 🪙 **Massive Token Savings:** Eliminates the need for AI agents to make dozens of `grep` or file-reading calls across hundreds of source files, saving thousands of prompt tokens and drastically lowering API context consumption.
- 🎯 **Pinpoint Navigation:** Every endpoint and SQL query in `architecture.json` links directly to its underlying file path (`controller.ts`, `router.py`, `repository.ts`), allowing AI agents to navigate straight to relevant files without scanning the entire repo.
- 🧠 **Living System Blueprint:** Gives AI models a structured, top-down mental model of your architecture that persists across chat sessions.

---

## Project Structure

```
arch-wiki/
├── SKILL.md              ← AI skill definition
├── README.md             ← This file
└── templates/
    └── build_html.py       ← HTML dashboard generator + architecture.json initialiser (~83 KB)
```

> `architecture.json` is automatically generated on first run by `build_html.py --init`
> via a **zero-dependency codebase scanner**. It automatically scans your `docker-compose.yml`,
> route files (`*.routes.ts`, `routers/*.py`), and `package.json` to populate endpoints,
> services, workspaces, permissions, prerequisites, and SQL queries without manual setup!
> Built-in deduplication automatically filters out build directories (`dist/`, `build/`, `node_modules/`)
> to prevent duplicate route definitions.

**In your target project**, the architecture setup is simple:

```
your-project/
└── docs/
    └── architecture/
        ├── architecture.json   ← Generated on first run (AI keeps updated)
        ├── build_html.py       ← Generator (copied from arch-wiki/templates/)
        └── architecture.html   ← Generated output (never edit manually)
```

---

## Quick Start (Installation & Setup)

### Option A: Install via `npx`

#### 1. From Git Repository (Hosted on GitHub/GitLab)
```bash
npx github:your-username/arch-wiki
```

#### 2. From Local Directory (Local Development without publishing)
```bash
# Point npx to your local folder:
npx ./path/to/arch-wiki

# OR run the installer directly with node:
node ./path/to/arch-wiki/bin/install.js

# OR use npm link for a global 'arch-wiki' command:
cd path/to/arch-wiki && npm link
```

#### 3. From NPM Registry (Once published)
```bash
npx arch-wiki
```

This automatically registers the `arch-wiki` skill into your AI assistant environment (`Antigravity`, `Claude Code`, `Cursor`, etc.).

---

### Option B: Manual File Copy

Copy `SKILL.md` into your AI tool's skills folder:

```bash
# Antigravity AI Agent
mkdir -p ~/.gemini/antigravity/skills/arch-wiki
cp SKILL.md ~/.gemini/antigravity/skills/arch-wiki/SKILL.md

# Claude Code
mkdir -p ~/.claude/skills/arch-wiki
cp SKILL.md ~/.claude/skills/arch-wiki/SKILL.md
```

---

## How to Use

Once installed, **you never need to run python scripts manually**. Simply open your AI coding assistant and ask:

> 💬 *"Run the `arch-wiki` skill on this project"*

The AI Assistant will autonomously:
1. Copy the codebase scanner engine into `docs/architecture/build_html.py`.
2. Scan Docker services (`docker-compose.yml`), API endpoints (`*.routes.ts`, `routers/*.py`), permissions, prerequisites, and SQL queries.
3. Create/Sync `docs/architecture/architecture.json`.
4. Generate the interactive dashboard at `docs/architecture/architecture.html`.

---

## Setup Guides

### Setup in Antigravity

Copy `SKILL.md` into your Antigravity skills directory:

```bash
# Option A: Copy as a named skill
cp arch-wiki/SKILL.md ~/.gemini/antigravity/skills/arch-wiki/SKILL.md

# Option B: Use directly from any project folder
# Just ensure the AI can access this SKILL.md file
```

Then invoke it by referencing the skill in your prompt:

```
Use the arch-wiki skill. I just added a new [module/endpoint/service].
```

---

### Setup in Claude Code / Cursor

Add `SKILL.md` to your project as a context file. You can either:

**Option A: Add to `.claude/` directory (Claude Code)**
```bash
mkdir -p your-project/.claude
cp arch-wiki/SKILL.md your-project/.claude/arch-wiki.md
```

**Option B: Add to `.cursor/rules/` (Cursor)**
```bash
mkdir -p your-project/.cursor/rules
cp arch-wiki/SKILL.md your-project/.cursor/rules/arch-wiki.md
```

Then prompt your AI:

```
Follow the instructions in .claude/arch-wiki.md / .cursor/rules/arch-wiki.md.
I just added a new module called [X].
```

---

### Setup in OpenAI Codex

Add the skill as a system instruction or paste it into the Codex context window:

```bash
# Print the skill content to paste into Codex
cat arch-wiki/SKILL.md
```

Or reference it as a file in your project and tell Codex:

```
Read and follow the instructions in arch-wiki/SKILL.md to update
my architecture documentation.
```

---

### Setup in OpenCode

Add `SKILL.md` to your OpenCode project context:

```bash
cp arch-wiki/SKILL.md your-project/arch-wiki.md
```

Then in your OpenCode session:

```
Read arch-wiki.md and follow its instructions to update docs/architecture/
after my recent changes to [module/service/endpoint].
```

---

### Setup for Any Other AI Tool

The skill is a plain Markdown file. Any AI assistant that can:
- Read files (`view_file` / `read_file`)
- Edit JSON files
- Execute shell commands (`python docs/architecture/build_html.py`)

...can use this skill. Simply provide the contents of `SKILL.md` as the system/context instruction.

---

## Simple Usage Examples

Because `arch-wiki` has a zero-dependency codebase scanner, you don't need to write long prompts or manually list your endpoints. Just tell your AI:

### Initial Setup
> 💬 *"Run `@arch-wiki` to generate architecture documentation for this project."*

### After Codebase Changes
> 💬 *"Run `@arch-wiki` to sync my architecture documentation with recent changes."*

The AI assistant will automatically run the codebase scanner, detect any new or updated endpoints, permissions, SQL queries, or Docker containers, and re-render `architecture.html`.

### 🤖 Interactive Senior Developer Endpoint Analysis Prompts

Clicking on **any API endpoint** in the **API Modules** view (or using its **📋 Prompt** button) opens an interactive modal with a tailor-made **Senior Developer Analysis Prompt**.

The prompt is dynamically formatted for the selected endpoint (e.g. `POST /api/v1/orders`), instructing an AI coding assistant to:
1. Act as a senior developer joining the project.
2. Analyze the endpoint using `architecture.json`, `arch-wiki` documentation, and project source code.
3. Discover the actual implementation flow and generate accurate **Mermaid sequence** and **flowchart** diagrams.
4. Adhere to strict boundaries (only include components and interactions that actually exist in code, do not infer missing components, do not modify code).

Includes a 1-click **📋 Copy to Clipboard** button directly on every endpoint card and inside the modal for instant integration with AI assistants.

---

## architecture.json Schema Reference

| Section | Purpose |
|---|---|
| `meta` | Project name, version, generated date, tech stack |
| `prerequisites` | Required runtime engines, infrastructure tools, databases, and setup steps |
| `workspaces` | Monorepo apps/packages (backend, frontend, packages) |
| `infrastructure` | Docker services (database, cache, queue, proxy, etc.) |
| `dockerDiagram` | Container topology nodes & edges for Mermaid diagram |
| `systemArchitectureDiagram` | Software component diagram nodes & edges |
| `swaggerSchemas` | OpenAPI spec metadata, servers, security scheme, schemas |
| `modules` | API modules with endpoints, permissions, file lists |
| `systemEndpoints` | Health/telemetry endpoints outside module structure |
| `coreLayer` | Middleware, core services, guards |
| `dataFlow` | Request pipeline steps (for the Request Pipeline view) |
| `permissions` | RBAC catalog (slugs list + detailed endpoint/page mappings) |
| `sqlQueries` | SQL query catalog with function, tables, purpose, endpoints |

---

## Framework Compatibility

The skill is designed to work with **any backend framework**. The AI adapts the source file scanning paths based on your stack:

| Framework | Route Files | Repository/Query Files |
|---|---|---|
| **Express / NestJS** | `src/modules/<name>/<name>.routes.ts` | `src/modules/<name>/<name>.repository.ts` |
| **FastAPI** | `app/routers/<name>.py` | `app/crud/<name>.py` |
| **Django** | `<app>/urls.py` + `views.py` | `<app>/models.py` |
| **Rails** | `config/routes.rb` + `app/controllers/` | `app/models/` |
| **Laravel** | `routes/api.php` + `app/Http/Controllers/` | `app/Models/` |
| **Spring Boot** | `src/.../controller/` | `src/.../repository/` |
| **Go (Gin/Echo)** | `internal/handler/` | `internal/repository/` |

---

## Dashboard Screenshots

The generated `architecture.html` includes 11 navigation sections:

| Section | Description |
|---|---|
| 📌 **Overview** | Stats cards + workspace list + system endpoints |
| 📋 **Prerequisites** | Developer tools, database runtimes, & step-by-step setup commands |
| 📦 **API Modules** | Searchable module cards with all endpoints & 1-click Senior Developer AI analysis prompt modals |
| 🏗️ **System Architecture** | Mermaid component diagram with pan/zoom toolbar & hand cursor |
| 🐋 **Docker Topology** | Mermaid container dependency graph with pan/zoom toolbar & hand cursor |
| ⚡ **Swagger & OpenAPI** | Live Swagger UI (Dark Theme), API catalog with cURL snippets, & OpenAPI JSON spec |
| 🔐 **Permissions & Scopes** | RBAC catalog, system scope fallbacks (authenticated/public), & scope-to-endpoint mapping |
| 🗃️ **SQL Queries** | Query catalog with SQL syntax highlighting |
| 🖥️ **Infrastructure** | Docker service cards with feature tags |
| 🛡️ **Core Layer** | Middleware and core service documentation |
| 🔄 **Request Pipeline** | Step-by-step request flow visualization |
| 📄 **PDF Export** | 1-click PDF generator that forces pre-rendering of diagrams, Swagger views, and scope mappings |


---

## Benchmark

The benchmark compares the same software understanding tasks using two approaches:

1. Direct AI exploration of the repository.
2. AI using `arch-wiki` and `architecture.json`.

The goal is not to measure token consumption only. The main goal is to evaluate whether `arch-wiki` can reduce repository exploration while producing a more accurate and useful architecture understanding.

### 1. Benchmark Prompts

| # | Task | Prompt |
|---|---|---|
| 1 | General Architecture | `Understand this project and explain: 1. Main architecture 2. Main modules 3. How an Order request flows through the system 4. Database interaction 5. External services. Do not modify anything.` |
| 2 | General Architecture with arch-wiki | Same prompt, with: `Use arch-wiki and architecture.json. Do not modify anything.` |
| 3 | Authentication Understanding | `You are joining this project as a new senior developer. You need to understand how authentication works. Explain: 1. Login flow 2. JWT generation 3. Refresh token flow 4. Database interaction 5. Redis interaction 6. Relevant files.` |
| 4 | Authentication with arch-wiki | Same prompt, with: `Use arch-wiki and architecture.json.` |
| 5 | Change Impact Analysis | `You need to add a new authentication feature. Find where this functionality should be implemented and explain which files would need to change and why. Do not modify anything.` |
| 6 | Change Impact Analysis with arch-wiki | Same prompt, with: `Use arch-wiki and architecture.json. Do not modify anything.` |

### 2. Results

| # | Approach | Exploration | Time | Result |
|---|---|---:|---:|---|
| 1 | Direct repository exploration | 17 files / 14 folders | ~2 min | Detailed architecture analysis with strong source-level details, but some conclusions were inaccurate or inferred. |
| 2 | `arch-wiki` + `architecture.json` | 1 file / 3 folders | ~1 min | Much faster and significantly less exploration. Produced a comprehensive architecture overview, but some details were inferred incorrectly. |
| 3 | Direct repository exploration | 7 files / 10 folders | ~1 min | Strong authentication analysis with detailed login, JWT, refresh token, DB and Redis flows. |
| 4 | `arch-wiki` + `architecture.json` | 7 files / 7 folders | ~1 min | Similar quality to direct exploration while using the architecture documentation to guide the investigation. |
| 5 | Direct repository exploration | 11 files / 20 folders | ~1 min | Good change impact analysis, but explored a relatively large part of the repository for an authentication-related task. |
| 6 | `arch-wiki` + `architecture.json` | 1 file / 6 folders | ~1 min | Much more focused exploration and produced a useful change-impact map based on the existing architecture. |

### 3. Opinion

| # | Task | Opinion |
|---|---|---|
| 1 vs 2 | General Architecture | **Major improvement.** `arch-wiki` reduced exploration from 17 files / 14 folders to 1 file / 3 folders while still producing a comprehensive architecture overview. The main weakness is that the AI may trust documented information too much and infer details that are not actually present in the source code. |
| 3 vs 4 | Authentication | **Very similar quality.** The direct approach explored 7 files / 10 folders, while the `arch-wiki` approach explored 7 files / 7 folders. This shows that the generated architecture information can guide the AI without sacrificing much accuracy. |
| 5 vs 6 | Change Impact | **Strong improvement.** The direct approach explored 11 files / 20 folders, while the `arch-wiki` approach explored only 1 file / 6 folders. The architecture manifest helped the AI identify the relevant architectural boundaries and affected files much faster. |

### 4. Initial Benchmark Conclusion

The most interesting result is not simply that `arch-wiki` makes the AI faster.

The important observation is:

> **The AI can use a pre-generated architecture representation as a map of the system instead of rediscovering the architecture from scratch for every question.**

In the tested scenarios, `arch-wiki` significantly reduced repository exploration, especially for high-level architecture and change-impact questions.

The benchmark also exposed an important limitation:

> **Architecture documentation must be accurate. If `architecture.json` contains incorrect or inferred information, the AI can propagate those mistakes instead of discovering the truth directly from the source code.**

Therefore, the next step is to measure **accuracy**, not just exploration reduction.


---

## 🚀 What's New in v1.1.0

Release **v1.1.0** represents a major architectural hardening release, bringing full enterprise **Spring Boot & Gradle Kotlin DSL (KTS)** support, AST-accurate lexer parsing, and robust real-world codebase discovery:

### ☕ Enterprise Spring Boot & Gradle Kotlin DSL Support
- **Full Kotlin DSL (`build.gradle.kts`, `settings.gradle.kts`) & Version Catalogs:** Extracts modules, dependencies, and Java toolchain versions from `libs.versions.toml` and Gradle scripts.
- **Maven Multi-Module & Java 21+:** Deep inspection of root and child `pom.xml` files with compiler release tracking and parent pom inheritance.
- **Actuator Endpoint Detection:** Auto-discovers enabled Spring Actuator endpoints (`/actuator/health`, `/actuator/info`, `/actuator/prometheus`).

### 🔍 Lexer-Based Annotation & Route Parsing
- Replaces fragile regular expressions with a state-machine Java lexer.
- Supports class-level × method-level Cartesian product route expansion (`@RequestMapping`, `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`).
- Handles Java comments, raw strings, multiline blocks, and mixed path arrays (`value = {"/api", "/v1"}`).

### 🔗 Cross-File Constant Resolution
- Automatically indexes repository `public static final String` constants.
- Resolves constant references across classes and packages for Kafka/messaging topic names and REST route path segments (e.g. `AppConstants.ORDERS_TOPIC` -> `"orders"`).

### 🗃️ Real SQL & JPQL Query Extraction
- Extracts explicit SQL and JPQL from `@Query` annotations, text blocks, and `JdbcTemplate` calls.
- **Chained CTE Isolation:** Correctly isolates and excludes chained Common Table Expressions (`WITH a AS (...), b AS (...)`), ensuring CTE aliases never leak into the database table catalog.
- **JPQL `JOIN FETCH` Protection:** Explicitly filters out `FETCH` keywords from JPQL association joins.

### 🐋 Docker Compose Multi-Folder Discovery & Edge Inference
- **Subfolder Search:** Automatically discovers `docker-compose*.yml` / `compose*.yml` up to 2 directories deep (`deployment/`, `docker/`, `infra/`, etc.).
- **Multi-File Merging:** Intelligently merges base compose files with environment overrides.
- **Runtime Edge Inference:** Infers runtime dependencies between services based on environment variables (`*_HOST`, `*_URL`, `KAFKA_BOOTSTRAP_SERVERS`, etc.).

### 🔐 SpEL Security Normalization & Object-Level RBAC
- Parses Spring Security `@PreAuthorize` SpEL expressions (`hasRole(...)`, `hasAuthority(...)`, `isAuthenticated()`, `permitAll()`).
- Identifies object-level security flags (`#id`, `@bean.method()`, `hasPermission(...)`).

### 🛠️ CLI Flags, Extensibility & CI/CD
- **`--skip-overrides` Flag:** Allows running raw codebase scans without triggering custom `arch_overrides.py` hooks.
- **`--placeholder-sql` Flag:** Backwards compatibility mode to preserve synthetic placeholder SQL counts for older workflows.
- **GitHub Actions CI:** Added automated CI test matrix in `.github/workflows/test.yml` running across Python 3.9 and Python 3.12.


## Requirements

- **Python 3.9+** (standard library — `json`, `re`, `os`, `sys`, `datetime` — no mandatory external dependencies; optional `pyyaml` for advanced Docker compose parsing)
- **Any AI assistant** that can read/write files and run shell commands
- **Docker is optional** — if `dockerDiagram.nodes` is empty, the Docker tab shows a friendly placeholder

---

## License

MIT — Use freely in any project.

---

## Contributing

To extend or adapt this skill:

1. Edit `SKILL.md` to add new sections or update instructions
2. Edit `templates/build_html.py` to add new dashboard sections
3. Update `templates/architecture.json` with new schema fields
4. Update this `README.md`

---

*Built with ❤️ for developers who want their architecture docs to stay alive.*
