---
name: arch-wiki
description: >
  Scans any project codebase for new/changed modules, endpoints, middleware,
  infrastructure, Docker topologies, SQL queries, or permissions and updates
  docs/architecture/architecture.json.
  Then regenerates docs/architecture/architecture.html by running build_html.py.
  Use this after any feature addition, module change, route update, SQL query,
  or architecture modification — for any backend framework (Express, NestJS,
  FastAPI, Django, Rails, Laravel, Spring, etc.).
---

# arch-wiki — Architecture Map & Interactive Swagger Sync Skill

> **Framework-agnostic** architecture documentation skill. Works with any project
> structure. Compatible with Antigravity, Claude Code, Cursor, Codex, OpenCode,
> and any AI assistant that can read files and run shell commands.

---

## When to invoke

- After adding a **new API module** (new folder/blueprint/controller group)
- After adding **new endpoints** to an existing module
- After adding **new middleware** or guards
- After adding **new core services** (cache, queue, email, logger, etc.)
- After adding **new Docker services** or updating `docker-compose.yml`
- After adding **new permissions** or updating permission-to-endpoint/admin-page mappings
- After writing **new SQL queries** or repository/service query methods
- After updating **Swagger/OpenAPI 3.0** route annotations or schemas
- After changing **ports, base paths, or tech stack**
- After adding a **new workspace** (monorepo app or package)

---

## Step-by-Step Instructions

### STEP 1 — Identify What Changed

Ask the user (or infer from context) exactly what changed:

- **New module?** Name, base path, controller/service/repo/routes files?
- **New endpoints?** Which module, method (GET/POST/PUT/PATCH/DELETE), path, auth flag, permission slug, description?
- **New Docker service / Topology change?** Service name, image, internal/external ports, network dependencies (`depends_on`), type?
- **New SQL query / Repository method?** Repository file, function name, SQL snippet, target tables, purpose, consuming API endpoints?
- **New permission mapping?** Permission slug, module/action details, mapped protected endpoints, mapped admin dashboard pages?
- **New Swagger schemas / OpenAPI spec updates?** OpenAPI version, servers, schemas, security scheme?
- **New middleware / core service?** File path, exported functions, security guards?
- **Meta changes?** Version bump, updated tech stack, generated date?

---

### STEP 2 — Setup & Codebase Execution

**1. Copy Template Script (if not present):**
Check if `docs/architecture/build_html.py` exists in the target project workspace.
If missing, ensure directory `docs/architecture` exists and copy `build_html.py` from the `arch-wiki` skill templates directory into `docs/architecture/build_html.py`.

**2. Run Script Execution:**

- **First-Time Setup (or Full Sync):**
  ```bash
  python docs/architecture/build_html.py --init
  ```
  *Scans project root metadata (`package.json`), Docker topology (`docker-compose.yml`), and API routes to create `architecture.json` and generate `architecture.html`.*

  Framework detection looks for `pom.xml`, `build.gradle` **or `build.gradle.kts` / `settings.gradle.kts`**
  (Spring Boot, Maven or Gradle incl. Kotlin DSL), then `package.json` (Express / NestJS / Fastify),
  then Python manifests (FastAPI / Django / Flask). For Java projects the Java and Spring Boot
  versions in `meta.techStack` are read from the build file (toolchain / `sourceCompatibility` /
  `<java.version>`, Spring Boot plugin or parent version, `gradle/libs.versions.toml`), and Gradle
  sub-projects from `settings.gradle(.kts)` become `workspaces`.

- **Incremental Sync (After Adding Features / Endpoints / Queries):**
  ```bash
  python docs/architecture/build_html.py --sync
  ```
  *Re-scans codebase for new endpoints, permissions, and SQL queries, updates `architecture.json`, and rebuilds `architecture.html`.*

> [!NOTE]
> The codebase scanner automatically excludes build artifacts (`dist/`, `build/`, `node_modules/`)
> to prevent duplicate route modules and sanitizes diagram nodes for error-free Mermaid rendering.

---

### STEP 3 — Update architecture.json

Apply targeted edits to `docs/architecture/architecture.json`.

**Rules for each section:**

#### 1. `meta`
- Bump `version` if significant architecture changes occurred
- Update `generatedAt` to today's date (`YYYY-MM-DD`)
- Add new tech stack entries under `techStack` if new dependencies were introduced

#### 2. `workspaces`
Add a new entry if a new app or package was created:
```json
{
  "id": "unique-id",
  "name": "apps/<folder>",
  "type": "backend|frontend|package",
  "description": "One-line description",
  "port": 3000,
  "entrypoint": "apps/<folder>/src/main.ts"
}
```

#### 3. `infrastructure`
Add a new entry for each Docker container/service:
```json
{
  "id": "service-id",
  "name": "Display Name + version",
  "type": "database|cache|queue|proxy|monitoring|logging|uptime",
  "image": "docker-image:tag",
  "port": 1234,
  "description": "What it does in this system",
  "features": ["feature 1", "feature 2"]
}
```

#### 4. `dockerDiagram`
Extracted from `docker-compose.yml` for rendering the container topology Mermaid diagram:
```json
{
  "description": "Container topology extracted from docker-compose.yml. Arrows represent network dependencies.",
  "nodes": [
    { "id": "node_id", "label": "Container Name", "type": "app|database|cache|queue|proxy|monitoring|logging|uptime", "port": 3000 }
  ],
  "edges": [
    { "from": "api", "to": "postgres", "label": "TCP 5432" }
  ]
}
```

#### 5. `systemArchitectureDiagram`
High-level software component and system design diagram rendered via Mermaid:
```json
{
  "description": "System architecture, software boundaries, and component relationships.",
  "subgraphs": [
    {
      "id": "layer_id",
      "label": "Layer Name",
      "nodes": [
        { "id": "node_id", "label": "Node Label", "type": "app|database|cache|queue" }
      ]
    }
  ],
  "edges": [
    { "from": "node_a", "to": "node_b", "label": "Protocol / Flow" }
  ]
}
```

#### 6. `swaggerSchemas`
Spec metadata and match status for the interactive Swagger UI and OpenAPI JSON generator:
```json
{
  "matchStatus": "Verified Parity (67/67 Endpoints)",
  "openapi": "3.0.0",
  "servedAt": "/api/docs",
  "securityScheme": "bearerAuth (JWT Bearer Token)",
  "servers": [
    { "url": "http://localhost:3000", "description": "Local Development Server" },
    { "url": "https://api.example.com", "description": "Production API Gateway" }
  ],
  "schemas": [
    { "name": "AuthTokensResponse", "description": "JWT accessToken and refreshToken pair" }
  ]
}
```

#### 7. `modules`
**Adding a new module:**
```json
{
  "id": "module-id",
  "name": "Module Name",
  "basePath": "/api/v1/<path>",
  "description": "What this module does",
  "color": "#6366f1",
  "icon": "emoji",
  "files": ["<name>.controller.ts", "<name>.service.ts", "<name>.repository.ts", "<name>.routes.ts"],
  "permissions": ["module:read", "module:write"],
  "endpoints": [
    {
      "method": "GET|POST|PUT|PATCH|DELETE",
      "path": "/path",
      "auth": true,
      "permission": "module:read or null",
      "description": "What this endpoint does",
      "handler": "ControllerClass.methodName (optional, filled by the Spring scanner)"
    }
  ]
}
```

> [!NOTE]
> **Spring:** the scanner parses every path of a mapping annotation (`@RequestMapping({"/a", "/b"})`,
> `value = {...}`, `path =` in any attribute position, `method = {POST, PUT}`) and emits one endpoint
> per class-level base × method path. A module's `basePath` is the longest common prefix of its
> controllers' class-level mappings and every endpoint `path` is relative to it, so
> `basePath + path` is always the real route. `@Operation(summary)` becomes the description,
> `@Tag(description)` the module description; `@PreAuthorize` / `@RolesAllowed` / `@Secured` are
> read anywhere in the method's annotation block, falling back to the class-level annotation.

#### 8. `permissions`
Keep `catalog` array sorted by module prefix.
Update `details` array with interactive flow connections:
```json
{
  "description": "RBAC permission catalog and permission-to-endpoint & page mapping.",
  "catalog": ["users:read", "users:write", "users:delete"],
  "details": [
    {
      "slug": "users:write",
      "module": "Users",
      "action": "UPDATE",
      "endpoints": [
        { "method": "PUT", "path": "/api/v1/users/:id" }
      ],
      "adminPages": ["User Management", "Edit User Form"]
    }
  ]
}
```

#### 9. `sqlQueries`
Catalog mapping raw SQL statements or query builders to repository functions and endpoints:
```json
{
  "id": "query-id",
  "label": "Query Title / Summary",
  "module": "Module Name",
  "file": "src/modules/module/module.repository.ts",
  "function": "RepositoryClass.methodName()",
  "tables": ["table1", "table2"],
  "purpose": "Detailed explanation of what the query accomplishes",
  "sql": "SELECT ... FROM table1 JOIN table2 ...",
  "endpoints": [
    { "method": "GET", "path": "/api/v1/module/resource" }
  ]
}
```

---

### STEP 4 — Regenerate HTML Dashboard

After updating `architecture.json`, execute the generator script from your project root:

```bash
python docs/architecture/build_html.py
```

**Docker is optional.** If `dockerDiagram.nodes` is empty, the Docker Topology tab shows a friendly "No Docker Services Configured" placeholder instead of an empty/broken Mermaid diagram. Add nodes only if your project uses Docker.

> [!IMPORTANT]
> Always verify that the top sticky header bar displays the platform title and badges **without navigation links**, and that all section links live in the left **NAVIGATION** sidebar.

---

### STEP 5 — Verify Dashboard in Browser

Verify `docs/architecture/architecture.html`:

1. **Top Header:** Brand title, subtitle, and badges (Version, Tech Stack, Generated Date) render at the top without navigation buttons.
2. **Left Sidebar:** All section buttons (`Overview`, `Prerequisites`, `API Modules`, `System Architecture`, `Docker Topology`, `Swagger & OpenAPI`, `Permissions`, `SQL Queries`, `Infrastructure`, `Core Layer`, `Request Pipeline`) are listed under `NAVIGATION`.
3. **Prerequisites Tab:** Software runtimes, container engines, database requirements, and step-by-step setup commands.
4. **Swagger & OpenAPI Tab:**
   - **Interactive Swagger UI:** Embedded native `SwaggerUIBundle` explorer with try-it-out functionality and dark theme overrides.
   - **API Catalog & cURL:** Endpoint list with copyable `cURL` request snippets.
   - **OpenAPI 3.0 JSON Spec:** Formatted JSON specification with 1-click copy button.
5. **Interactive Diagrams:** System Architecture and Docker Topology render cleanly via Mermaid.js with interactive pan/zoom toolbars and hand (grab) cursor feedback.
6. **SQL Queries:** Full system query catalog displayed with syntax highlighting and mapped endpoints.

---

## Quick-Use Prompt Templates

### Prompt A — "I added a new module"

```
Run arch-wiki to update the architecture map.

I just added a new module called [MODULE_NAME]:
- Files: src/modules/[name]/
- Base path: /api/v1/[path]
- Permissions needed: [list permissions]
- Endpoints:
  - GET / → [description] → permission: [x]
  - POST / → [description] → permission: [x]

Read docs/architecture/architecture.json, add the new module entry,
update permissions.catalog and details arrays,
then run: python docs/architecture/build_html.py
```

### Prompt B — "I added endpoints to an existing module"

```
Run arch-wiki to update the architecture map.

I added new endpoints to the [MODULE_NAME] module (id: [module-id]):
- [METHOD] [path] → [description] → permission: [x] or null

Read docs/architecture/architecture.json, find module with id "[module-id]",
add the new endpoints, update permissions.catalog,
then run: python docs/architecture/build_html.py
```

### Prompt C — "I updated Docker services or topology"

```
Run arch-wiki to update the architecture map.

I added/updated Docker services in docker-compose.yml:
- Service: [Name], Image: [image:tag], Port: [port], Type: [type]
- Inter-service connections: [from] -> [to] via [protocol]

Read docs/architecture/architecture.json, update infrastructure and dockerDiagram arrays,
then run: python docs/architecture/build_html.py
```

### Prompt D — "I added a new SQL Query or Repository Method"

```
Run arch-wiki to update the architecture map.

I added a new SQL query / repository function:
- File: src/modules/[module]/[file]
- Function: [ClassName.methodName()]
- SQL: "[SELECT ...]"
- Tables: [table1, table2]
- Purpose: [Explanation of what the query does]
- Mapped Endpoints: [METHOD /api/v1/path]

Read docs/architecture/architecture.json, append to sqlQueries array,
then run: python docs/architecture/build_html.py
```

### Prompt E — "I updated permissions or page mappings"

```
Run arch-wiki to update the architecture map.

I updated permission mappings:
- Permission Slug: [slug]
- Action: [READ|WRITE|DELETE]
- Mapped Endpoints: [METHOD /path]
- Admin Dashboard Pages: [Page Name]

Read docs/architecture/architecture.json, update permissions.details,
then run: python docs/architecture/build_html.py
```

### Prompt F — "Full Rescan & Parity Audit"

```
Run arch-wiki to rescan the codebase and sync the architecture map.

1. Read docs/architecture/architecture.json to inspect current manifest
2. Audit actual codebase:
   - Entry point / app bootstrap (route registrations, system endpoints)
   - All module route files (endpoints, permissions, swagger annotations)
   - All repository files (SQL queries, DB operations)
   - Middleware directory
   - docker-compose.yml (infrastructure & container topology)
3. Apply all edits to architecture.json
4. Run: python docs/architecture/build_html.py
5. Verify parity and report additions/changes
```
