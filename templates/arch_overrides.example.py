"""arch-wiki project override hook — copy to docs/architecture/arch_overrides.py

build_html.py calls `apply(data, root)` after every scanner has run and writes
whatever you return as architecture.json. Use it to merge a source of truth the
generic scanners cannot know about:

  • a permission catalog file (slug → label / admin page / description)
  • a frontend API client that maps HTTP calls to the pages using them
  • hand-maintained endpoint ↔ SQL query links, extra system endpoints,
    corrected base paths, service descriptions, tech-stack details …

Contract
--------
    def apply(data: dict, root: str) -> dict | None

`data`  — the complete manifest (meta, modules, permissions, sqlQueries,
          infrastructure, dockerDiagram, …). Mutate it in place or build a
          new dict; returning None keeps `data`.
`root`  — absolute path of the scanned project root.

Nothing is recomputed after the hook except swaggerSchemas.matchStatus, so if
you change endpoint permissions rebuild the catalog yourself with
`build_html.build_permissions(modules)` (see below). Raise to abort the run.

Only the standard library is guaranteed; the hook runs with the same Python
as build_html.py (3.9+).
"""
import json
import os
import re


def _load_permission_catalog(root):
    """Example: docs/permissions.json → {slug: {"label": …, "pages": […], "description": …}}."""
    for cand in ('docs/permissions.json', 'src/main/resources/permissions.json'):
        p = os.path.join(root, cand)
        if os.path.isfile(p):
            with open(p, encoding='utf-8') as f:
                raw = json.load(f)
            return {e['slug']: e for e in raw} if isinstance(raw, list) else raw
    return {}


def _frontend_api_usage(root):
    """Example: map "METHOD /path" → [page names] from a TypeScript API client.

    Looks for calls like `api.get('/api/v1/invoices')` / `http.post(\"/api/…\")`
    under frontend/src and attributes them to the page folder they live in.

    It reads every source file under frontend/src on each run. For a large
    frontend narrow the walk to the API-client folder (e.g. frontend/src/api)
    or cache the result keyed on the newest mtime — the hook runs on every
    --init / --sync.
    """
    usage = {}
    fe = os.path.join(root, 'frontend', 'src')
    if not os.path.isdir(fe):
        return usage
    call_re = re.compile(r"\b(?:api|http|client|axios)\.(get|post|put|patch|delete)\s*\(\s*[`'\"]([^`'\"]+)[`'\"]")
    for r, _, files in os.walk(fe):
        for fn in files:
            if not fn.endswith(('.ts', '.tsx', '.js', '.jsx', '.vue')):
                continue
            rel = os.path.relpath(os.path.join(r, fn), fe).replace('\\', '/')
            page = rel.split('/')[1] if rel.startswith('pages/') and '/' in rel[6:] else rel.split('/')[0]
            with open(os.path.join(r, fn), encoding='utf-8', errors='ignore') as f:
                txt = f.read()
            for m in call_re.finditer(txt):
                path = re.sub(r'\$\{[^}]+\}', '{id}', m.group(2)).split('?')[0]
                usage.setdefault(f"{m.group(1).upper()} {path}", set()).add(page.title())
    return {k: sorted(v) for k, v in usage.items()}


def apply(data, root):
    catalog = _load_permission_catalog(root)
    usage = _frontend_api_usage(root)

    # 1. Enrich permission details from the catalog file (labels / admin pages)
    for det in data.get('permissions', {}).get('details', []):
        entry = catalog.get(det['slug'])
        if entry:
            det['adminPages'] = list(entry.get('pages') or entry.get('adminPages') or det['adminPages'])
            if entry.get('description'):
                det['description'] = entry['description']

    # 2. Attach frontend pages to the endpoints that call them
    if usage:
        for mod in data.get('modules', []):
            for ep in mod.get('endpoints', []):
                full = (mod['basePath'] + ('' if ep['path'] == '/' else ep['path'])).replace('//', '/')
                pages = usage.get(f"{ep['method']} {full}")
                if pages:
                    ep['pages'] = pages
        for det in data.get('permissions', {}).get('details', []):
            pages = sorted({pg for e in det['endpoints'] for pg in usage.get(f"{e['method']} {e['path']}", [])})
            if pages:
                det['adminPages'] = pages

    # 3. Example of a hard correction the scanners cannot infer
    for svc in data.get('infrastructure', []):
        if svc['id'] == 'keycloak':
            svc['description'] = 'Identity provider — issues the JWTs verified by the API'

    # 4. If you changed endpoint permissions above, rebuild the catalog:
    #    import build_html
    #    data['permissions'] = build_html.build_permissions(data['modules'])
    return data
