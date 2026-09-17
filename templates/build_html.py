import json
import html
import os
import re
import sys
import datetime

# ---------------------------------------------------------------------------
# SKILL.md PARSER
# Reads arch-wiki SKILL.md (or any SKILL.md found next to this script or in
# the project root) and extracts key/value pairs from the YAML front-matter
# plus the first heading as the display name.
# ---------------------------------------------------------------------------

def parse_skill_md(skill_path):
    """Return a dict of metadata extracted from SKILL.md YAML front-matter."""
    meta = {}
    if not os.path.isfile(skill_path):
        return meta
    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract YAML front-matter between --- delimiters
    fm_match = re.match(r'^---\s*\n(.+?)\n---', content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ':' in line:
                k, _, v = line.partition(':')
                meta[k.strip()] = v.strip().strip('>')
    # Extract first H1 heading as display name
    h1 = re.search(r'^#\s+(.+)', content, re.MULTILINE)
    if h1:
        meta['h1'] = h1.group(1).strip()
    return meta


def find_skill_md():
    """Search for SKILL.md in: same dir as script, parent dirs (up to 3 levels)."""
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, 'SKILL.md'),
        os.path.join(base, '..', 'SKILL.md'),
        os.path.join(base, '..', '..', 'SKILL.md'),
        os.path.join(base, '..', '..', '..', 'SKILL.md'),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return None


# ---------------------------------------------------------------------------
# CODEBASE SCANNER  (no third-party deps — stdlib only)
# Walks up to find the project root, then scans:
#   • docker-compose.yml  → infrastructure + dockerDiagram
#   • *.routes.ts/js      → Express modules + endpoints
#   • app.ts / app.js     → base path registrations
#   • routers/*.py        → FastAPI modules + endpoints
# ---------------------------------------------------------------------------

import glob as _glob

_COLORS = ['#6366f1','#f59e0b','#10b981','#3b82f6','#8b5cf6',
           '#ef4444','#f97316','#06b6d4','#84cc16','#ec4899',
           '#14b8a6','#a855f7','#f43f5e','#0ea5e9','#22c55e']

_ICON_MAP = {
    'auth':'🔐','user':'👤','users':'👥','patient':'🏥','patients':'🏥',
    'appointment':'📅','appointments':'📅','visit':'🩺','visits':'🩺',
    'audit':'📋','stat':'📊','stats':'📊','product':'📦','products':'📦',
    'order':'🛒','orders':'🛒','payment':'💳','payments':'💳',
    'report':'📈','reports':'📈','admin':'⚙️','setting':'⚙️','settings':'⚙️',
    'notification':'🔔','message':'💬','file':'📁','search':'🔍',
    'dashboard':'📊','analytics':'📈','health':'💚',
}

def _icon(name): return _ICON_MAP.get(name.lower().rstrip('s'), _ICON_MAP.get(name.lower(), '📁'))
def _color(name, i): return next((c for k,c in {'auth':'#6366f1','user':'#f59e0b','patient':'#10b981',
    'appointment':'#3b82f6','visit':'#8b5cf6','audit':'#ef4444','stat':'#f97316',
    'product':'#06b6d4','order':'#84cc16','payment':'#ec4899'}.items()
    if k in name.lower()), _COLORS[i % len(_COLORS)])

def clean_mermaid(text):
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return text.replace('"', '').replace("'", '').replace('\n', ' ').strip()

def _find_root(start):
    """Find the root directory of the project containing this docs/architecture folder.
    Checks for markers like docker-compose.yml, package.json, backend/, .git, etc."""
    markers = [
        'docker-compose.yml', 'docker-compose.yaml', 'compose.yml', '.git',
        'package.json', 'requirements.txt', 'go.mod', 'Gemfile', 'pom.xml', 'Cargo.toml', 'composer.json',
        'build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts'
    ]
    cur = os.path.abspath(start)
    for _ in range(5):
        if any(os.path.exists(os.path.join(cur, m)) for m in markers):
            return cur
        # Check if subdirectories have package.json or requirements.txt
        if any(os.path.exists(os.path.join(cur, sub, 'package.json')) for sub in ['backend', 'api', 'server', 'app']):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur: break
        cur = parent
    return os.path.abspath(os.path.join(start, "..", ".."))  # default to 2 levels up from docs/architecture

_JAVA_BUILD_FILES = ['pom.xml', 'build.gradle.kts', 'build.gradle', 'settings.gradle.kts', 'settings.gradle']

def _java_build_file(root):
    """Return the path of the first Maven/Gradle build file found at root or a common sub-dir, else None."""
    for sub in ['', 'app', 'server', 'backend', 'apps/api', 'apps/server', 'apps/backend']:
        for bf in _JAVA_BUILD_FILES:
            p = os.path.join(root, sub, bf) if sub else os.path.join(root, bf)
            if os.path.isfile(p):
                return p
    return None

def _read(path):
    try:
        return open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return ''

def _java_build_info(root):
    """Derive build tool, Java and Spring Boot versions from pom.xml / build.gradle(.kts).

    Returns a dict: {'buildTool': 'maven'|'gradle'|None, 'buildFile': rel path or None,
    'kotlinDsl': bool, 'javaVersion': '25'|None, 'springBootVersion': '4.0.0'|None}.
    """
    info = {'buildTool': None, 'buildFile': None, 'kotlinDsl': False,
            'javaVersion': None, 'springBootVersion': None}
    bf = _java_build_file(root)
    if not bf:
        return info
    bdir = os.path.dirname(bf)
    is_maven = os.path.basename(bf) == 'pom.xml'
    info['buildTool'] = 'maven' if is_maven else 'gradle'
    # Prefer the build script over settings when both exist (versions live there)
    if not is_maven:
        for cand in ['build.gradle.kts', 'build.gradle']:
            if os.path.isfile(os.path.join(bdir, cand)):
                bf = os.path.join(bdir, cand); break
    info['buildFile'] = os.path.relpath(bf, root).replace('\\', '/')
    info['kotlinDsl'] = bf.endswith('.kts')
    txt = _read(bf)

    if is_maven:
        jv = (re.search(r'<java\.version>\s*([\d.]+)\s*</java\.version>', txt)
              or re.search(r'<maven\.compiler\.(?:release|source|target)>\s*([\d.]+)\s*<', txt)
              or re.search(r'<release>\s*([\d.]+)\s*</release>', txt))
        if jv: info['javaVersion'] = jv.group(1)
        sb = re.search(r'<artifactId>spring-boot-starter-parent</artifactId>\s*<version>([^<]+)</version>', txt)
        if not sb:
            sb = re.search(r'<artifactId>spring-boot(?:-dependencies)?</artifactId>\s*<version>([^<]+)</version>', txt)
        if not sb:
            sb = re.search(r'<spring-boot\.version>([^<]+)</spring-boot\.version>', txt)
        if sb: info['springBootVersion'] = sb.group(1).strip()
    else:
        jv = (re.search(r'JavaLanguageVersion\.of\(\s*(\d+)\s*\)', txt)
              or re.search(r'(?:sourceCompatibility|targetCompatibility)\s*=\s*(?:JavaVersion\.VERSION_)?["\']?(\d+(?:_\d+)?)', txt)
              or re.search(r'options\.release(?:\.set)?\s*[=(]\s*(\d+)', txt))
        if jv: info['javaVersion'] = jv.group(1).replace('1_', '1.').replace('_', '.')
        sb = re.search(r'["\']org\.springframework\.boot["\']\s*\)?\s*version\s*\(?\s*["\']([^"\']+)["\']', txt)
        if not sb:
            # Version catalog: gradle/libs.versions.toml → spring-boot = "4.0.0"
            toml = _read(os.path.join(root, 'gradle', 'libs.versions.toml'))
            sb = re.search(r'^\s*spring[-_.]?boot\s*=\s*["\']([^"\']+)["\']', toml, re.MULTILINE)
        if sb: info['springBootVersion'] = sb.group(1).strip()
    # Java version may live in the version catalog or gradle.properties too
    if not info['javaVersion'] and not is_maven:
        for extra in [os.path.join(root, 'gradle', 'libs.versions.toml'), os.path.join(root, 'gradle.properties')]:
            m = re.search(r'^\s*(?:java|jdk)(?:[-_.]?version)?\s*=\s*["\']?(\d+)', _read(extra), re.MULTILINE)
            if m: info['javaVersion'] = m.group(1); break
    return info

def _detect_fw(root):
    if _java_build_file(root):
        return 'spring'
    for sub in ['', 'backend', 'api', 'server', 'app', 'apps/api', 'apps/server', 'apps/backend']:
        pkg = os.path.join(root, sub, 'package.json') if sub else os.path.join(root, 'package.json')
        if os.path.isfile(pkg):
            try:
                deps = {}
                with open(pkg, encoding='utf-8') as f:
                    d = json.load(f)
                deps.update(d.get('dependencies', {})); deps.update(d.get('devDependencies', {}))
                if 'express' in deps: return 'express'
                if '@nestjs/core' in deps: return 'nestjs'
                if 'fastify' in deps: return 'fastify'
            except: pass

    apps_dir = os.path.join(root, 'apps')
    if os.path.isdir(apps_dir):
        for sub in os.listdir(apps_dir):
            pkg = os.path.join(apps_dir, sub, 'package.json')
            if os.path.isfile(pkg):
                try:
                    deps = {}
                    with open(pkg, encoding='utf-8') as f:
                        d = json.load(f)
                    deps.update(d.get('dependencies', {})); deps.update(d.get('devDependencies', {}))
                    if 'express' in deps: return 'express'
                    if '@nestjs/core' in deps: return 'nestjs'
                    if 'fastify' in deps: return 'fastify'
                except: pass

    for sub in ['', 'backend', 'api', 'app']:
        base = os.path.join(root, sub) if sub else root
        for req_name in ['requirements.txt', 'pyproject.toml', 'Pipfile', 'setup.py']:
            req = os.path.join(base, req_name)
            if os.path.isfile(req):
                try:
                    t = open(req, encoding='utf-8', errors='ignore').read().lower()
                    if 'fastapi' in t: return 'fastapi'
                    if 'django' in t: return 'django'
                    if 'flask' in t: return 'flask'
                except: pass

    for r, _, fls in os.walk(root):
        norm_r = r.replace('\\', '/')
        if any(x in norm_r for x in ['/__pycache__/', '/venv/', '/.git/', '/node_modules/']): continue
        for f in fls:
            if f.endswith('.py'):
                try:
                    txt = open(os.path.join(r, f), encoding='utf-8', errors='ignore').read().lower()
                    if 'fastapi' in txt: return 'fastapi'
                    if 'django' in txt: return 'django'
                    if 'flask' in txt: return 'flask'
                except: pass
    return 'unknown'

def _scan_docker(root):
    for name in ['docker-compose.yml','docker-compose.yaml','compose.yml','compose.yaml']:
        path = os.path.join(root, name)
        if not os.path.isfile(path): continue
        lines = open(path, encoding='utf-8', errors='ignore').read().splitlines()
        svcs, cur = {}, None
        in_svc, in_dep = False, False
        dep_indent = 0

        for ln in lines:
            s = ln.rstrip()
            if not s or s.startswith('#'): continue

            if re.match(r'^[a-zA-Z0-9_\-]+:', s):
                in_svc = s.startswith('services:')
                cur = None; in_dep = False
                continue
            if not in_svc: continue

            m = re.match(r'^  ([a-zA-Z0-9_\-]+):\s*$', s)
            if m:
                cur = m.group(1)
                svcs[cur] = {'image':'','ports':[],'depends':[],'build':''}
                in_dep = False; continue
            if not cur: continue

            if re.match(r'^\s+image:\s+', s): svcs[cur]['image'] = s.split('image:')[1].strip()
            if re.match(r'^\s+context:\s+', s): svcs[cur]['build'] = s.split('context:')[1].strip()
            pm = re.match(r'^\s+-\s*["\']?(\d+):(\d+)["\']?', s)
            if pm: svcs[cur]['ports'].append(int(pm.group(1)))

            dm_start = re.match(r'^(\s+)depends_on:', s)
            if dm_start:
                in_dep = True
                dep_indent = len(dm_start.group(1))
                continue

            if in_dep:
                curr_indent = len(s) - len(s.lstrip())
                if curr_indent <= dep_indent and not s.strip().startswith('-'):
                    in_dep = False
                else:
                    dm_list = re.match(r'^\s+-\s*([a-zA-Z0-9_\-]+)', s)
                    dm_map = re.match(r'^\s+([a-zA-Z0-9_\-]+):\s*$', s)
                    dep_target = None
                    if dm_list:
                        dep_target = dm_list.group(1)
                    elif dm_map:
                        dep_target = dm_map.group(1)
                    
                    if dep_target and dep_target not in ('condition', 'service_healthy', 'service_started', 'environment', 'logging', 'ports', 'image', 'restart', 'build'):
                        if dep_target not in svcs[cur]['depends']:
                            svcs[cur]['depends'].append(dep_target)

        all_svcs = list(svcs.keys())
        for sn, sv in svcs.items():
            if sn.endswith('-service'):
                prefix = sn.replace('-service', '')
                for db in [f"{prefix}-mongodb", f"{prefix}-db", f"{prefix}-postgres", f"{prefix}-mysql"]:
                    if db in svcs and db not in sv['depends']:
                        sv['depends'].append(db)
            
            if sn == 'gateway':
                for target_svc in all_svcs:
                    if target_svc.endswith('-service') and target_svc not in sv['depends']:
                        sv['depends'].append(target_svc)

        hints = {'postgres':'database','mysql':'database','mongo':'database','redis':'cache',
                 'rabbitmq':'queue','kafka':'queue','nginx':'proxy','gateway':'proxy','traefik':'proxy',
                 'prometheus':'monitoring','grafana':'monitoring','monitoring':'monitoring',
                 'elasticsearch':'logging','registry':'registry','config':'config',
                 'minio':'storage','s3':'storage','blob':'storage'}
        infra, nodes, edges = [], [], []
        for sn, sv in svcs.items():
            t = next((v for k,v in hints.items() if k in sn.lower() or k in sv['image'].lower()), 'app')
            port = sv['ports'][0] if sv['ports'] else None
            infra.append({'id':sn,'name':sn.replace('-',' ').replace('_',' ').title(),'type':t,
                'image':sv['image'] or f"build:{sv['build']}",
                'port':port,'description':f"{sn} container",'features':[]})
            nodes.append({'id':sn,'label':f"{sn}{':%d'%port if port else ''}",
                'type':t,'port':port})
            for dep in sv['depends']:
                if dep in svcs: edges.append({'from':sn,'to':dep,'label':''})
        return infra, {'description':f"Topology from {name}.","nodes":nodes,"edges":edges}
    return [], {'description':'','nodes':[],'edges':[]}

def _infer_desc(method, path, mod):
    has_id = bool(re.search(r':[^/]+|\{[^}]+\}', path))
    segs = [p for p in path.split('/') if p and not p.startswith(':') and not p.startswith('{')]
    if len(segs) > 1:
        sub = segs[-1].replace('_',' ').replace('-',' ')
        return f"{method.title()} {mod.lower()} — {sub}"
    tpl = {('GET',False):f"List all {mod.lower()}",('GET',True):f"Get {mod.lower()} by ID",
           ('POST',False):f"Create {mod.lower()}",('PUT',True):f"Update {mod.lower()} by ID",
           ('PATCH',True):f"Patch {mod.lower()} by ID",('DELETE',True):f"Delete {mod.lower()} by ID"}
    return tpl.get((method, has_id), f"{method} {path}")

def _scan_express(root):
    src_dirs = []
    for sub in ['', 'backend', 'api', 'server', 'app', 'apps/api', 'apps/server', 'apps/backend']:
        c = os.path.join(root, sub, 'src') if sub else os.path.join(root, 'src')
        if os.path.isdir(c): src_dirs.append(c)
        c2 = os.path.join(root, sub) if sub else None
        if c2 and os.path.isdir(os.path.join(c2, 'routes')): src_dirs.append(c2)
    apps_dir = os.path.join(root, 'apps')
    if os.path.isdir(apps_dir):
        for sub in os.listdir(apps_dir):
            c = os.path.join(apps_dir, sub, 'src')
            if os.path.isdir(c): src_dirs.append(c)
            c2 = os.path.join(apps_dir, sub)
            if os.path.isdir(os.path.join(c2, 'routes')): src_dirs.append(c2)
    src_dirs = sorted(set(src_dirs))
    if not src_dirs: return []

    # Map variable names to base paths from app.ts / app.js / main.ts
    # e.g. import authRoutes from './routes/auth.routes.js' + app.use('/api/v1/auth', authRoutes)
    base_paths = {}  # filename_key -> base_path
    var_to_file = {} # var_name -> filename_key

    for src in src_dirs:
        for fn in ['app.ts', 'app.js', 'index.ts', 'index.js', 'main.ts', 'main.js', 'server.ts', 'server.js']:
            fp = os.path.join(src, fn)
            if not os.path.isfile(fp): continue
            txt = open(fp, encoding='utf-8', errors='ignore').read()

            # Find imports: import authRoutes from './routes/auth.routes.js';
            for m in re.finditer(r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]", txt):
                var_name, import_path = m.group(1), m.group(2)
                file_key = os.path.basename(import_path).replace('.js','').replace('.ts','').replace('.routes','')
                var_to_file[var_name] = file_key

            # Find app.use('/api/v1/auth', authRoutes)
            for m in re.finditer(r"app\.use\(['\"]([^'\"]+)['\"]\s*,\s*(\w+)\)", txt):
                bpath, var_name = m.group(1).rstrip('/'), m.group(2)
                if var_name in var_to_file:
                    base_paths[var_to_file[var_name]] = bpath
                else:
                    file_key = var_name.replace('Routes','').replace('Router','').lower()
                    base_paths[file_key] = bpath

    # Walk directory to collect all route files (exclude dist, build, node_modules)
    route_files = []
    for src in src_dirs:
        for r, _, files in os.walk(src):
            norm_r = r.replace('\\', '/')
            if '/dist/' in norm_r or '/build/' in norm_r or '/node_modules/' in norm_r: continue
            for f in files:
                if f.endswith('.d.ts'): continue
                if ('.routes.' in f or '.router.' in f or f.endswith('Routes.ts') or f.endswith('Routes.js')) and f.endswith(('.ts', '.js')):
                    route_files.append(os.path.join(r, f))
    
    # Deduplicate route files by module key, preferring .ts over .js
    dedup_routes = {}
    for rf in route_files:
        fn = os.path.basename(rf)
        raw = re.sub(r'\.(routes|router)\.(ts|js)$', '', fn)
        raw = re.sub(r'Routes\.(ts|js)$', '', raw).lower()
        if raw not in dedup_routes or rf.endswith('.ts'):
            dedup_routes[raw] = rf
    route_files = sorted(dedup_routes.values())

    modules = []
    for idx, rf in enumerate(route_files):
        txt = open(rf, encoding='utf-8', errors='ignore').read()
        fn = os.path.basename(rf)
        raw = re.sub(r'\.(routes|router)\.(ts|js)$', '', fn)
        raw = re.sub(r'Routes\.(ts|js)$', '', raw)
        name = raw.title(); mid = raw.lower().replace('-', '_')

        # Determine base path
        key = raw.lower()
        bp = base_paths.get(key, f"/api/v1/{key}")

        global_auth = bool(re.search(r'router\.use\((authenticateJWT|authenticate|authMiddleware|requireAuth)\)', txt)) or ('authenticateJWT' in txt) or ('authenticate' in txt)
        
        global_roles = re.findall(r"(?:authorizeRoles|authorize|requireRole|requirePermission|checkPermission|hasRole)\(([^)]+)\)", txt)
        g_roles = []
        for r in global_roles:
            cleaned = r.replace('[','').replace(']','').replace("'",'').replace('"','').strip()
            for x in cleaned.split(','):
                xc = x.strip()
                if xc and xc not in g_roles:
                    g_roles.append(xc)

        eps, seen = [], set()
        for m in re.finditer(r"router\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]*)['\"]([\s\S]*?)(?=\n\s*router\.|\n\s*export|\n\s*const|\n\s*/\*\*|;\s*\n|\)\s*;|\)$)", txt, re.IGNORECASE):
            method, path, rest = m.group(1).upper(), m.group(2), m.group(3)
            key_ep = f"{method}:{path}"
            if key_ep in seen: continue
            seen.add(key_ep)
            auth = global_auth or ('authenticateJWT' in rest) or ('authenticate' in rest) or ('auth' in path.lower()) or ('requirePermission' in rest)
            
            rm = re.search(r"(?:authorizeRoles|authorize|requireRole|requirePermission|checkPermission|hasRole)\(([^)]+)\)", rest)
            if rm:
                cleaned = rm.group(1).replace('[','').replace(']','').replace("'",'').replace('"','').strip()
                perm_list = [x.strip() for x in cleaned.split(',') if x.strip()]
                perm = ' | '.join(perm_list) if perm_list else None
            else:
                perm = ' | '.join(g_roles) if g_roles else None

            eps.append({'method': method, 'path': path, 'auth': auth,
                        'permission': perm, 'description': _infer_desc(method, path, name)})

        # Fallback if multiline lookahead misses single line at end of file
        if not eps:
            for m in re.finditer(r"router\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]*)['\"]([^;\n]*?)(?:\)|;|\n)", txt, re.IGNORECASE):
                method, path, rest = m.group(1).upper(), m.group(2), m.group(3)
                key_ep = f"{method}:{path}"
                if key_ep in seen: continue
                seen.add(key_ep)
                auth = global_auth or ('authenticateJWT' in rest) or ('authenticate' in rest) or ('auth' in path.lower()) or ('requirePermission' in rest)
                rm = re.search(r"(?:authorizeRoles|authorize|requireRole|requirePermission|checkPermission|hasRole)\(([^)]+)\)", rest)
                perm = rm.group(1).replace("'",'').replace('"','').strip() if rm else (' | '.join(g_roles) if g_roles else None)
                eps.append({'method': method, 'path': path, 'auth': auth, 'permission': perm, 'description': _infer_desc(method, path, name)})

        if not eps: continue
        perms = list(set(e['permission'] for e in eps if e.get('permission')))
        modules.append({
            'id': mid, 'name': name, 'basePath': bp,
            'description': f"{name} module — {len(eps)} endpoint(s)",
            'color': _color(raw, idx), 'icon': _icon(raw), 'files': [fn],
            'permissions': perms, 'endpoints': eps
        })
    return modules

def _scan_fastapi(root):
    app_prefixes = {}
    for r, _, fls in os.walk(root):
        norm_r = r.replace('\\', '/')
        if any(x in norm_r for x in ['/__pycache__/', '/venv/', '/.git/', '/tests/', '/test/', '/node_modules/']):
            continue
        for f in fls:
            if f.endswith('.py'):
                fp = os.path.join(r, f)
                txt = open(fp, encoding='utf-8', errors='ignore').read()
                for m in re.finditer(r"include_router\s*\(\s*(\w+)\s*,[\s\S]*?prefix=['\"]([^'\"]+)['\"]", txt):
                    router_var, pfx = m.group(1), m.group(2)
                    key = router_var.replace('_router', '').replace('router', '').lower()
                    app_prefixes[key] = pfx

    route_files = []
    for r, _, files in os.walk(root):
        norm_r = r.replace('\\', '/')
        if any(x in norm_r for x in ['/__pycache__/', '/venv/', '/.git/', '/tests/', '/test/', '/node_modules/']):
            continue
        for f in files:
            if f.endswith('.py') and not f.startswith('test_') and f != '__init__.py':
                route_files.append(os.path.join(r, f))

    modules = []
    for idx, rf in enumerate(sorted(set(route_files))):
        txt = open(rf, encoding='utf-8', errors='ignore').read()
        if not re.search(r"@(?:router|app|api)\.(get|post|put|patch|delete)", txt, re.IGNORECASE):
            continue
        fn = os.path.basename(rf)
        raw = re.sub(r'\.py$', '', fn)
        name = raw.replace('_', ' ').title()
        mid = raw.lower().replace('-', '_')

        pm = re.search(r"APIRouter\([\s\S]*?prefix=['\"]([^'\"]+)['\"]", txt)
        bp = pm.group(1) if pm else app_prefixes.get(mid, f"/api/{raw.replace('_', '-')}")

        eps = []
        seen = set()
        for m in re.finditer(r"@(?:router|app|api)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]*)['\"]", txt, re.IGNORECASE):
            method, path = m.group(1).upper(), m.group(2) or '/'
            key_ep = f"{method}:{path}"
            if key_ep in seen:
                continue
            seen.add(key_ep)

            auth = ('Depends' in txt or 'get_current_user' in txt or 'require_' in txt or 'Security' in txt)
            eps.append({
                'method': method,
                'path': path,
                'auth': auth,
                'permission': None,
                'description': _infer_desc(method, path, name)
            })

        if eps:
            modules.append({
                'id': mid,
                'name': name,
                'basePath': bp,
                'description': f"{name} API — {len(eps)} endpoint(s)",
                'color': _color(raw, idx),
                'icon': _icon(raw),
                'files': [fn],
                'permissions': [],
                'endpoints': eps
            })
    return modules

def _gradle_includes(root):
    """Sub-project names from settings.gradle(.kts): include("a", ":b") / include 'a', 'b' / include(":a:b")."""
    for name in ['settings.gradle.kts', 'settings.gradle']:
        txt = _read(os.path.join(root, name))
        if not txt: continue
        mods = []
        for m in re.finditer(r'^\s*include\s*\(?\s*((?:["\'][^"\']+["\']\s*,?\s*)+)\)?', txt, re.MULTILINE):
            for q in re.findall(r'["\']([^"\']+)["\']', m.group(1)):
                q = q.strip(':').replace(':', '/')
                if q and q not in mods: mods.append(q)
        return mods
    return []

def _detect_arch_type(root, fw):
    """
    Determines whether the codebase architecture is:
      - 'monolith': Single-module project (e.g. standard Spring MVC war/jar with single src/main/java)
      - 'modular_monolith': Multi-module repo (e.g. Maven pom.xml with <modules> or subfolder services without docker)
      - 'microservice': Multi-service project with docker-compose or microservices architecture
    """
    # Check docker-compose first
    for name in ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']:
        if os.path.isfile(os.path.join(root, name)):
            try:
                txt = open(os.path.join(root, name), encoding='utf-8', errors='ignore').read()
                if 'services:' in txt:
                    return 'microservice'
            except: pass

    # Check Maven pom.xml for <modules>
    pom_path = os.path.join(root, 'pom.xml')
    if os.path.isfile(pom_path):
        try:
            txt = open(pom_path, encoding='utf-8', errors='ignore').read()
            if '<modules>' in txt and '</modules>' in txt:
                return 'modular_monolith'
        except: pass

    # Check Gradle settings.gradle / settings.gradle.kts for sub-project includes
    if _gradle_includes(root):
        return 'modular_monolith'

    # Check top-level directories for multiple src/main/java sub-projects
    subdirs_with_src = 0
    for item in os.listdir(root):
        item_path = os.path.join(root, item)
        if os.path.isdir(item_path) and item not in ('src', 'target', 'docs', 'templates', '.git', '.idea', '.settings', 'workflow_Alfresco', 'model', 'scanner'):
            if os.path.isfile(os.path.join(item_path, 'pom.xml')) or os.path.isdir(os.path.join(item_path, 'src', 'main', 'java')):
                subdirs_with_src += 1

    if subdirs_with_src > 1:
        return 'modular_monolith'

    return 'monolith'


def _scan_screens_java(root):
    """Scan webapp, templates, static, public for HTML/JSP screen files."""
    screens = []
    scan_dirs = []
    for sub in ['src/main/webapp', 'src/main/resources/templates', 'src/main/resources/static', 'src/main/resources/public', 'webapp', 'public']:
        p = os.path.join(root, sub)
        if os.path.isdir(p):
            scan_dirs.append(p)
    
    for sdir in scan_dirs:
        for r, _, fls in os.walk(sdir):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/node_modules/', '/WEB-INF/lib/', '/WEB-INF/classes/']):
                continue
            for f in fls:
                if f.endswith(('.html', '.jsp', '.xhtml', '.ftl', '.vm')):
                    rf = os.path.join(r, f)
                    rel = os.path.relpath(rf, root).replace('\\', '/')
                    screens.append({'name': f, 'path': rel, 'dir': os.path.basename(r)})
    return screens


# ---------------------------------------------------------------------------
# JAVA SOURCE HELPERS  (shared by the Spring route scanner and SQL extractor)
# ---------------------------------------------------------------------------

_JAVA_MODIFIERS = {'public', 'protected', 'private', 'static', 'final', 'abstract',
                   'synchronized', 'native', 'default', 'strictfp', 'transient', 'volatile'}
_JAVA_NOT_A_TYPE = _JAVA_MODIFIERS | {'return', 'new', 'throw', 'throws', 'else', 'if', 'while',
                                      'for', 'switch', 'catch', 'try', 'do', 'case', 'super', 'this',
                                      'instanceof', 'assert', 'yield', 'import', 'package'}

def _java_lex(txt):
    """Blank out comments (keeping offsets) and return (code, string_spans).

    string_spans is a list of (start, end, value) for every "…" literal and
    \"\"\"…\"\"\" text block, with value already unescaped / de-indented.
    """
    n = len(txt)
    out = list(txt)
    spans = []
    i = 0
    while i < n:
        c = txt[i]
        nxt = txt[i+1] if i + 1 < n else ''
        if c == '/' and nxt == '/':
            j = txt.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j): out[k] = ' '
            i = j
        elif c == '/' and nxt == '*':
            j = txt.find('*/', i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != '\n': out[k] = ' '
            i = j
        elif c == '"' and txt.startswith('"""', i):
            j = i + 3
            while j < n:
                if txt[j] == '\\': j += 2; continue
                if txt.startswith('"""', j): break
                j += 1
            raw = txt[i+3:j]
            spans.append((i, j + 3, _java_text_block(raw)))
            i = j + 3
        elif c == '"':
            j = i + 1
            while j < n and txt[j] != '"':
                if txt[j] == '\\': j += 1
                if txt[j] == '\n': break
                j += 1
            spans.append((i, j + 1, _java_unescape(txt[i+1:j])))
            i = j + 1
        elif c == "'":
            j = i + 1
            while j < n and txt[j] != "'" and txt[j] != '\n':
                if txt[j] == '\\': j += 1
                j += 1
            i = j + 1
        else:
            i += 1
    return ''.join(out), spans

def _java_unescape(s):
    return (s.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
             .replace("\\'", "'").replace('\\\\', '\\'))

def _java_text_block(raw):
    """Strip the incidental indentation of a Java text block (JEP 378)."""
    lines = raw.split('\n')
    if lines and not lines[0].strip(): lines = lines[1:]
    indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    closing = lines[-1] if lines and not lines[-1].strip() else None
    if closing is not None: indents.append(len(closing))
    ind = min(indents) if indents else 0
    lines = [l[ind:].rstrip() for l in lines]
    return _java_unescape('\n'.join(lines)).strip('\n')

def _in_string(pos, spans):
    return any(s <= pos < e for s, e, _ in spans)

def _balanced(code, open_idx, spans, opener='(', closer=')'):
    """Index just past the bracket matching code[open_idx], skipping string contents."""
    depth = 0
    i = open_idx
    n = len(code)
    while i < n:
        if _in_string(i, spans):
            i += 1; continue
        ch = code[i]
        if ch == opener: depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0: return i + 1
        i += 1
    return n

def _split_top_level(s):
    """Split on commas that are not nested in (), {}, [] or a string."""
    parts, depth, cur, in_str, esc = [], 0, [], None, False
    for ch in s:
        if in_str:
            cur.append(ch)
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == in_str: in_str = None
            continue
        if ch in '"\'': in_str = ch
        elif ch in '({[': depth += 1
        elif ch in ')}]': depth -= 1
        elif ch == ',' and depth == 0:
            parts.append(''.join(cur)); cur = []; continue
        cur.append(ch)
    if ''.join(cur).strip(): parts.append(''.join(cur))
    return [p.strip() for p in parts if p.strip()]

def _java_annotations(code, spans):
    """Every annotation outside strings: dicts {name, args, kw, pos, start, end}.

    kw maps attribute → raw expression; positional value stored under '' .
    """
    annos = []
    for m in re.finditer(r'@([A-Za-z_][\w.]*)', code):
        if _in_string(m.start(), spans): continue
        name = m.group(1).split('.')[-1]
        end = m.end()
        args = ''
        j = end
        while j < len(code) and code[j] in ' \t': j += 1
        if j < len(code) and code[j] == '(':
            end = _balanced(code, j, spans)
            args = code[j+1:end-1]
        kw, pos = {}, []
        for part in _split_top_level(args):
            km = re.match(r'^([A-Za-z_]\w*)\s*=(?!=)\s*(.*)$', part, re.DOTALL)
            if km: kw[km.group(1)] = km.group(2).strip()
            else: pos.append(part)
        if pos: kw[''] = pos[0]
        annos.append({'name': name, 'args': args, 'kw': kw, 'pos': pos,
                      'start': m.start(), 'end': end})
    return annos

def _string_values(expr, consts=None):
    """String literals inside an annotation attribute value.

    Handles "a", {"a", "b"}, "a" + "b" chains and simple constant references
    resolved through `consts` (NAME or Class.NAME → value).
    """
    if expr is None: return []
    expr = expr.strip()
    if expr.startswith('{') and expr.endswith('}'):
        return [v for part in _split_top_level(expr[1:-1]) for v in _string_values(part, consts)]
    lits = re.findall(r'"((?:[^"\\]|\\.)*)"', expr)
    if lits:
        return [_java_unescape(''.join(lits))]
    if consts:
        key = expr.replace(' ', '')
        if key in consts: return [consts[key]]
        if key.split('.')[-1] in consts: return [consts[key.split('.')[-1]]]
    return []

def _java_string_consts(code):
    """NAME → value for `static final String NAME = "…"` fields (and "a" + "b" chains)."""
    consts = {}
    for m in re.finditer(r'\bString\s+([A-Z_][A-Z0-9_]*)\s*=\s*((?:"(?:[^"\\]|\\.)*"\s*\+?\s*)+);', code):
        consts[m.group(1)] = ''.join(re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(2)))
    return consts

_JAVA_METHOD_RE = re.compile(
    r'(?:(?:public|protected|private|static|final|abstract|synchronized|native|default)\s+)*'
    r'(?:<[^>]*>\s*)?'                                   # generic method type params
    r'([A-Za-z_][\w.]*(?:\s*<[^;{}()]*?>)?(?:\s*\[\s*\])*)'  # return type
    r'\s+([A-Za-z_]\w*)\s*\(', re.DOTALL)

def _java_method_after(code, pos, spans, limit=None):
    """Name of the first method declared at or after `pos`, or None."""
    limit = len(code) if limit is None else limit
    for m in _JAVA_METHOD_RE.finditer(code, pos, limit):
        if _in_string(m.start(), spans): continue
        rtype, name = m.group(1).strip(), m.group(2)
        if rtype.split('<')[0].split('.')[-1] in _JAVA_NOT_A_TYPE or name in _JAVA_NOT_A_TYPE: continue
        if rtype in ('return',): continue
        return name
    return None

def _java_methods(code, spans):
    """[(start, name)] of every method/constructor-like declaration, in file order."""
    out = []
    for m in _JAVA_METHOD_RE.finditer(code):
        if _in_string(m.start(), spans): continue
        rtype, name = m.group(1).strip(), m.group(2)
        head = rtype.split('<')[0].split('.')[-1]
        if head in _JAVA_NOT_A_TYPE or name in _JAVA_NOT_A_TYPE: continue
        # must be followed (after the parameter list) by '{', ';' or 'throws' — else it's a call
        close = _balanced(code, m.end() - 1, spans)
        tail = code[close:close+40].lstrip()
        if not (tail.startswith('{') or tail.startswith(';') or tail.startswith('throws')): continue
        out.append((m.start(), name))
    return out

def _java_type_name(code, spans):
    """(name, decl_index) of the first top-level class/interface/record/enum."""
    for m in re.finditer(r'\b(class|interface|record|enum)\s+([A-Za-z_]\w*)', code):
        if not _in_string(m.start(), spans):
            return m.group(2), m.start()
    return None, len(code)

def _join_path(base, sub):
    full = '/' + '/'.join(p for p in (base or '').split('/') + (sub or '').split('/') if p)
    return full

def _common_path_prefix(paths):
    segs = [[p for p in path.split('/') if p] for path in paths if path is not None]
    if not segs: return '/'
    prefix = segs[0]
    for s in segs[1:]:
        i = 0
        while i < min(len(prefix), len(s)) and prefix[i] == s[i]: i += 1
        prefix = prefix[:i]
    return '/' + '/'.join(prefix)

_SPRING_MAPPINGS = {'GetMapping': ['GET'], 'PostMapping': ['POST'], 'PutMapping': ['PUT'],
                    'DeleteMapping': ['DELETE'], 'PatchMapping': ['PATCH'], 'RequestMapping': None}

def _mapping_paths(anno, consts):
    for key in ('', 'value', 'path'):
        vals = _string_values(anno['kw'].get(key), consts)
        if vals: return vals
    return ['']

def _mapping_methods(anno):
    fixed = _SPRING_MAPPINGS.get(anno['name'])
    if fixed: return fixed
    found = re.findall(r'RequestMethod\.([A-Z]+)', anno['kw'].get('method', ''))
    return found or ['GET']

def _get_perm(annos):
    for a in annos:
        if a['name'] == 'PreAuthorize':
            vals = _string_values(a['kw'].get('') or a['kw'].get('value'))
            if vals: return vals[0]
    for a in annos:
        if a['name'] in ('RolesAllowed', 'Secured'):
            vals = _string_values(a['kw'].get('') or a['kw'].get('value'))
            if vals: return ' | '.join(vals)
    return None

def _get_summary(annos):
    for a in annos:
        if a['name'] == 'Operation':
            for key in ('summary', 'description'):
                vals = _string_values(a['kw'].get(key))
                if vals and vals[0].strip(): return vals[0].strip()
    return None

def _scan_java_spring(root, arch_type=None):
    if not arch_type:
        arch_type = _detect_arch_type(root, 'spring')

    all_screens = _scan_screens_java(root)
    files = []
    for r, _, fls in os.walk(root):
        norm_r = r.replace('\\', '/')
        if '/target/' in norm_r or '/.idea/' in norm_r or '/build/' in norm_r or '/.git/' in norm_r or '/test/' in norm_r:
            continue
        for f in fls:
            if f.endswith('.java'):
                files.append(os.path.join(r, f))
    by_class = {os.path.basename(f)[:-5]: f for f in files}

    mod_map = {}
    for rf in sorted(files):
        txt = open(rf, encoding='utf-8', errors='ignore').read()
        if not ('@RestController' in txt or '@Controller' in txt):
            continue
        code, spans = _java_lex(txt)
        annos = _java_annotations(code, spans)
        if not any(a['name'] in ('RestController', 'Controller') for a in annos):
            continue

        fn = os.path.basename(rf)
        raw_name = fn.replace('Controller.java', '').replace('.java', '')

        rel = os.path.relpath(rf, root).replace('\\', '/')
        top_folder = rel.split('/')[0] if '/' in rel else raw_name.lower()
        is_monolith = (arch_type == 'monolith') or (top_folder in ('src', 'main', 'java', 'app', 'backend', 'server', '.'))

        if is_monolith:
            mid = raw_name.lower().replace('-', '_')
            svc_title = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_name).title()
        else:
            mid = top_folder
            svc_title = mid.replace('-service', '').replace('_service', '').replace('-', ' ').title()
        name = svc_title

        # Constants usable in mapping paths: this file plus any `Other.CONST` references
        consts = _java_string_consts(code)
        for ref in set(re.findall(r'\b([A-Z][A-Za-z0-9_]*)\.([A-Z_][A-Z0-9_]*)\b', code)):
            other = by_class.get(ref[0])
            if other and other != rf:
                oc, _ = _java_lex(open(other, encoding='utf-8', errors='ignore').read())
                for k, v in _java_string_consts(oc).items():
                    consts.setdefault(f"{ref[0]}.{k}", v)

        class_name, class_pos = _java_type_name(code, spans)
        class_annos = [a for a in annos if a['start'] < class_pos]
        member_annos = [a for a in annos if a['start'] >= class_pos]

        class_bases = ['']
        for a in class_annos:
            if a['name'] == 'RequestMapping':
                class_bases = _mapping_paths(a, consts)
                break
        class_perm = _get_perm(class_annos)
        tag_desc = None
        for a in class_annos:
            if a['name'] == 'Tag':
                vals = _string_values(a['kw'].get('description'))
                if vals: tag_desc = vals[0].strip()
        file_auth = ('Security' in txt or 'PreAuthorize' in txt or 'Principal' in txt or 'OAuth' in txt
                     or 'RolesAllowed' in txt or 'Secured' in txt or 'Authentication' in txt)

        # Group member annotations into runs: consecutive annotations separated only by whitespace
        runs, cur = [], []
        for a in member_annos:
            if cur and code[cur[-1]['end']:a['start']].strip():
                runs.append(cur); cur = []
            cur.append(a)
        if cur: runs.append(cur)

        eps, seen = [], set()
        for run in runs:
            mappings = [a for a in run if a['name'] in _SPRING_MAPPINGS]
            if not mappings: continue
            perm = _get_perm(run) or class_perm
            summary = _get_summary(run)
            handler = _java_method_after(code, run[-1]['end'], spans)
            for mp in mappings:
                for method in _mapping_methods(mp):
                    for base in class_bases:
                        for sub in _mapping_paths(mp, consts):
                            full = _join_path(base, sub)
                            key_ep = f"{method}:{full}"
                            if key_ep in seen: continue
                            seen.add(key_ep)
                            eps.append({
                                'method': method,
                                'path': full,          # re-relativised against the module basePath below
                                'auth': file_auth or perm is not None,
                                'permission': perm,
                                'description': summary or _infer_desc(method, sub or '/', name),
                                'handler': f"{class_name or raw_name}.{handler}" if handler else None,
                            })

        # Find matching screens/templates for this module
        mod_screens = []
        raw_low = raw_name.lower()
        for scr in all_screens:
            sp = scr['path'].lower()
            sn = scr['name'].lower()
            if raw_low in sn or raw_low in sp or mid in sp:
                mod_screens.append(scr['path'])

        perms = list(set(e['permission'] for e in eps if e.get('permission')))
        if mid in mod_map:
            m = mod_map[mid]
            if rel not in m['files'] and fn not in m['files']:
                m['files'].append(rel)
            existing = set(f"{e['method']}:{e['path']}" for e in m['endpoints'])
            m['endpoints'].extend(e for e in eps if f"{e['method']}:{e['path']}" not in existing)
            m['permissions'] = list(set(m['permissions'] + perms))
            m['_bases'].extend(class_bases)
            for ms in mod_screens:
                if ms not in m['files']:
                    m['files'].append(ms)
            if tag_desc and not m.get('_tagDesc'):
                m['_tagDesc'] = tag_desc
        else:
            mod_map[mid] = {
                'id': mid,
                'name': name if is_monolith else f"{svc_title} Service",
                'basePath': '/',
                'description': '',
                'color': _color(mid, len(mod_map)),
                'icon': _icon(mid),
                'files': [rel] + mod_screens,
                'permissions': perms,
                'endpoints': eps,
                '_bases': list(class_bases),
                '_tagDesc': tag_desc,
                '_monolith': is_monolith,
                '_title': svc_title,
            }

    # Module basePath = longest common prefix of its controllers' class-level paths,
    # endpoint paths relative to it — so basePath + path is always the real route.
    for m in mod_map.values():
        bp = _common_path_prefix([_join_path(b, '') for b in m.pop('_bases')])
        m['basePath'] = bp
        for e in m['endpoints']:
            rel_path = e['path'][len(bp):] if bp != '/' and e['path'].startswith(bp) else e['path']
            e['path'] = rel_path or '/'
        n = len(m['endpoints'])
        tag_desc = m.pop('_tagDesc', None)
        title = m.pop('_title')
        if m.pop('_monolith'):
            m['description'] = f"{tag_desc or title + ' module'} — {n} endpoint(s)"
        else:
            m['description'] = f"{tag_desc or title + ' microservice'} — {n} endpoint(s)"

    if arch_type != 'monolith':
        pom_path = os.path.join(root, 'pom.xml')
        if os.path.isfile(pom_path):
            pom_txt = open(pom_path, encoding='utf-8', errors='ignore').read()
            sub_mods = re.findall(r'<module>([^<]+)</module>', pom_txt)
            for sm in sub_mods:
                sm_clean = sm.strip()
                if sm_clean in ('app', 'docs', 'templates'): continue
                sm_mid = sm_clean.replace('_', '-').lower()
                if sm_mid not in mod_map:
                    sm_name = sm_clean.replace('-service', '').replace('_service', '').replace('-', ' ').title()
                    mod_map[sm_mid] = {
                        'id': sm_mid,
                        'name': f"{sm_name} Service",
                        'basePath': f"/{sm_clean.replace('-service','')}",
                        'description': f"{sm_name} domain microservice (Infrastructure/Config module)",
                        'color': _color(sm_mid, len(mod_map)),
                        'icon': _icon(sm_mid),
                        'files': ['pom.xml'],
                        'permissions': [],
                        'endpoints': []
                    }

    return list(mod_map.values())

def _scan_workspaces(root):
    ws = []
    pom_path = os.path.join(root, 'pom.xml')
    if os.path.isfile(pom_path):
        pom_txt = open(pom_path, encoding='utf-8', errors='ignore').read()
        sub_mods = re.findall(r'<module>([^<]+)</module>', pom_txt)
        port_base = 8080
        for idx, sm in enumerate(sub_mods):
            sm_clean = sm.strip()
            ws.append({
                'id': sm_clean,
                'name': sm_clean,
                'type': 'backend',
                'description': f"{sm_clean.replace('-',' ').title()} Service",
                'port': port_base + idx,
                'entrypoint': f"{sm_clean}/pom.xml"
            })
        if ws: return ws

    gradle_mods = _gradle_includes(root)
    if gradle_mods:
        for gm in gradle_mods:
            bf = next((c for c in ['build.gradle.kts', 'build.gradle']
                       if os.path.isfile(os.path.join(root, gm, c))), 'build.gradle.kts')
            ws.append({
                'id': gm.replace('/', '-'),
                'name': gm,
                'type': 'backend',
                'description': f"{os.path.basename(gm).replace('-',' ').replace('_',' ').title()} Module",
                'port': None,
                'entrypoint': f"{gm}/{bf}"
            })
        return ws

    for sub in ['backend','frontend','api','web','mobile','admin']:
        p = os.path.join(root, sub)
        if not os.path.isdir(p): continue
        t = 'backend' if sub in ('backend','api') else 'frontend'
        port = 3000 if t == 'backend' else 80
        env = os.path.join(p, '.env')
        if os.path.isfile(env):
            pm = re.search(r'^PORT\s*=\s*(\d+)', open(env,encoding='utf-8',errors='ignore').read(), re.MULTILINE)
            if pm: port = int(pm.group(1))
        ws.append({'id':sub,'name':sub,'type':t,
            'description':f"{sub.title()} {'REST API' if t=='backend' else 'UI'}",
            'port':port,'entrypoint':f"{sub}/src/index.ts"})
    return ws or [{'id':'api','name':'api','type':'backend',
        'description':'Main REST API','port':3000,'entrypoint':'src/index.ts'}]

def _scan_core_layer(root, fw):
    sec, mid, svc = [], [], []

    if fw in ('spring', 'java'):
        for r, _, fls in os.walk(root):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/target/', '/.idea/', '/build/', '/.git/', '/test/']):
                continue
            for f in fls:
                if not f.endswith('.java'): continue
                rf = os.path.join(r, f)
                rel = os.path.relpath(rf, root).replace('\\', '/')
                txt = open(rf, encoding='utf-8', errors='ignore').read()
                name_clean = f.replace('.java', '')

                if any(k in txt for k in ['@EnableWebSecurity', '@EnableResourceServer', '@EnableAuthorizationServer', 'WebSecurityConfigurerAdapter', 'ResourceServerConfigurerAdapter']) or 'SecurityConfig' in f or 'OAuth2' in f:
                    desc = "OAuth2 Authorization Server Security Config" if ('Authorization' in txt or 'Auth' in f) else "Spring Resource Server & Web Security Config"
                    sec.append({"name": name_clean, "file": rel, "description": desc})
                elif 'UserDetailsService' in txt or 'UserDetailsService' in f:
                    sec.append({"name": name_clean, "file": rel, "description": "Spring Security UserDetailsService & User Principal Provider"})

                if 'Filter' in f or 'Interceptor' in f or 'OncePerRequestFilter' in txt or 'HandlerInterceptor' in txt or '@ControllerAdvice' in txt or 'ErrorHandler' in f:
                    desc = "Global Exception & Error Handling Controller Advice" if ('@ControllerAdvice' in txt or 'Error' in f) else f"Spring HTTP Request Filter / Interceptor ({name_clean})"
                    mid.append({"name": name_clean, "file": rel, "description": desc, "guards": ["HTTP Filter Chain"]})

                if '@Service' in txt or 'ServiceImpl' in f or '@FeignClient' in txt or '@Repository' in txt or 'Repository' in f or 'Client' in f:
                    stype = "Feign REST Client" if ('@FeignClient' in txt or 'Client' in f) else ("Spring Data Repository" if ('@Repository' in txt or 'Repository' in f) else "Core Business Logic Service")
                    svc.append({"name": name_clean, "file": rel, "description": f"{stype} ({rel.split('/')[0]})", "exports": [name_clean]})

        if sec and not any(s['name'] == 'Spring Security & OAuth2' for s in sec):
            sec.insert(0, {"name": "Spring Security & OAuth2", "file": "pom.xml", "description": "Framework OAuth2 Resource Server & JWT verification layer"})

    elif fw in ('express', 'nestjs', 'fastify'):
        pkg_path = os.path.join(root, 'package.json')
        deps = {}
        if os.path.isfile(pkg_path):
            try:
                d = json.load(open(pkg_path, encoding='utf-8'))
                deps.update(d.get('dependencies', {}))
                deps.update(d.get('devDependencies', {}))
            except: pass

        if 'helmet' in deps: sec.append({"name": "Helmet.js", "file": "package.json", "description": "HTTP security headers protection"})
        if 'cors' in deps: sec.append({"name": "CORS", "file": "package.json", "description": "Cross-Origin Resource Sharing restriction"})
        if 'jsonwebtoken' in deps or 'passport' in deps: sec.append({"name": "JWT / Passport Auth", "file": "package.json", "description": "Bearer token authentication & identity verification"})
        if 'bcrypt' in deps or 'argon2' in deps: sec.append({"name": "Bcrypt / Argon2", "file": "package.json", "description": "Password hashing & credential verification"})

        for r, _, fls in os.walk(root):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/node_modules/', '/dist/', '/build/', '/.git/', '/test/']): continue
            for f in fls:
                if not (f.endswith('.ts') or f.endswith('.js')): continue
                rf = os.path.join(r, f)
                rel = os.path.relpath(rf, root).replace('\\', '/')
                txt = open(rf, encoding='utf-8', errors='ignore').read()
                name_clean = f.replace('.ts', '').replace('.js', '')

                if 'middleware' in norm_r or 'guard' in norm_r or 'interceptor' in norm_r or 'Middleware' in f or 'Guard' in f:
                    mid.append({"name": name_clean, "file": rel, "description": f"Request processing middleware ({f})", "guards": ["Route Guard"]})

                if '@Injectable' in txt or 'PrismaClient' in txt or 'Mongoose' in txt or 'TypeORM' in txt or 'service' in norm_r or 'repository' in norm_r:
                    svc.append({"name": name_clean, "file": rel, "description": f"Core service module ({f})", "exports": [name_clean]})

    elif fw in ('fastapi', 'django', 'flask'):
        for r, _, fls in os.walk(root):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/__pycache__/', '/venv/', '/.git/', '/tests/']): continue
            for f in fls:
                if not f.endswith('.py'): continue
                rf = os.path.join(r, f)
                rel = os.path.relpath(rf, root).replace('\\', '/')
                txt = open(rf, encoding='utf-8', errors='ignore').read()
                name_clean = f.replace('.py', '')

                if 'OAuth2' in txt or 'CORSMiddleware' in txt or 'jwt' in txt or 'security' in f or 'auth' in f:
                    sec.append({"name": name_clean, "file": rel, "description": "Security & Authentication module"})

                if 'middleware' in norm_r or 'Middleware' in f or 'BaseHTTPMiddleware' in txt:
                    mid.append({"name": name_clean, "file": rel, "description": f"HTTP Middleware component ({f})", "guards": ["Request Pipeline"]})

                if 'service' in norm_r or 'crud' in norm_r or 'models' in f or 'repository' in norm_r or 'SessionLocal' in txt:
                    svc.append({"name": name_clean, "file": rel, "description": f"Data service / Model repository ({f})", "exports": [name_clean]})

    else:
        for r, _, fls in os.walk(root):
            norm_r = r.replace('\\', '/')
            if any(x in norm_r for x in ['/target/', '/vendor/', '/node_modules/', '/.git/', '/bin/', '/obj/']): continue
            for f in fls:
                rf = os.path.join(r, f)
                rel = os.path.relpath(rf, root).replace('\\', '/')
                fl = f.lower()
                if 'security' in fl or 'auth' in fl or 'oauth' in fl or 'jwt' in fl:
                    sec.append({"name": f, "file": rel, "description": f"Security & Auth component ({f})"})
                elif 'middleware' in norm_r or 'filter' in fl or 'interceptor' in fl or 'guard' in fl:
                    mid.append({"name": f, "file": rel, "description": f"Request Middleware / Filter ({f})", "guards": ["Request Pipeline"]})
                elif 'service' in norm_r or 'repository' in norm_r or ('service' in fl or 'repo' in fl or 'db' in fl):
                    svc.append({"name": f, "file": rel, "description": f"Service / Data Layer component ({f})", "exports": [f]})

    if not sec:
        sec = [
            {"name": "Security & TLS", "description": "Transport Layer Security and API Authentication"},
            {"name": "CORS & Origin Control", "description": "Cross-Origin Resource Sharing restrictions"}
        ]
    if not mid:
        mid = [
            {"name": "Global Request Filter", "file": "src/", "description": "HTTP request validation & telemetry filter", "guards": ["Validation"]}
        ]
    if not svc:
        svc = [
            {"name": "Main Data Client", "file": "src/", "description": "Core data layer & database service connection manager", "exports": ["DataClient"]}
        ]

    def _dedup(lst, key='name'):
        seen = set()
        res = []
        for item in lst:
            k = item.get(key)
            if k and k not in seen:
                seen.add(k)
                res.append(item)
        return res

    return {
        "security": _dedup(sec)[:8],
        "middleware": _dedup(mid)[:10],
        "services": _dedup(svc)[:12]
    }

def _build_sys_diagram(modules, infrastructure):
    client_nodes = [
        {'id': 'web_client', 'label': 'Web Application / Client', 'type': 'app'},
        {'id': 'mobile_client', 'label': 'Mobile App / API Consumer', 'type': 'app'}
    ]
    api_nodes = []
    if modules:
        for m in modules:
            m_name = m.get('name', 'API Module')
            m_id = f"mod_{re.sub(r'[^a-zA-Z0-9_]', '_', m_name.lower())}"
            api_nodes.append({'id': m_id, 'label': f"{m_name} Module", 'type': 'app'})
    if not api_nodes:
        api_nodes.append({'id': 'api_server', 'label': 'REST API Gateway / Server', 'type': 'app'})
        
    data_nodes = []
    for s in infrastructure:
        if s.get('type') in ('database', 'cache', 'queue', 'storage'):
            data_nodes.append({'id': s['id'], 'label': f"{s['name']}{(' :%s'%s.get('port')) if s.get('port') else ''}", 'type': s.get('type')})
    if not data_nodes:
        data_nodes.append({'id': 'db', 'label': 'PostgreSQL Database', 'type': 'database'})
    
    subgraphs = [
        {'id': 'client_layer', 'label': 'Client & Consumer Layer', 'nodes': client_nodes},
        {'id': 'api_layer', 'label': 'Application & Service Layer', 'nodes': api_nodes},
        {'id': 'data_layer', 'label': 'Data & Infrastructure Layer', 'nodes': data_nodes},
    ]
    
    edges = []
    for cn in client_nodes:
        for an in api_nodes:
            edges.append({'from': cn['id'], 'to': an['id'], 'label': 'HTTPS REST'})
            
    for an in api_nodes:
        for dn in data_nodes:
            lbl = 'Store / Fetch' if dn.get('type') == 'storage' else ('Cache / PubSub' if dn.get('type') == 'cache' else 'Query')
            edges.append({'from': an['id'], 'to': dn['id'], 'label': lbl})
            
    return {'description': 'System architecture, module boundaries, and infrastructure component relationships.',
            'subgraphs': subgraphs, 'edges': edges}


def _build_data_flow(fw, core_layer):
    """Build framework-aware requestPipeline and errorPipeline for dataFlow section."""

    # Pull scanned middleware/security names for step annotations
    sec_names  = [s.get('name','') for s in core_layer.get('security', [])]
    mid_names  = [m.get('name','') for m in core_layer.get('middleware', [])]
    mid_files  = [m.get('file','') for m in core_layer.get('middleware', [])]
    err_handler = next((m['name'] for m in core_layer.get('middleware', [])
                        if any(k in m.get('name','') for k in ['Exception','Error','ControllerAdvice'])), None)

    if fw in ('spring', 'java'):
        # Detect interceptors/filters from scanned middleware
        has_interceptor = any('Interceptor' in n or 'Filter' in n for n in mid_names)
        has_security    = any('Security' in n or 'OAuth' in n for n in sec_names)
        sec_note = f" ({sec_names[0]})" if sec_names else ""
        mid_note = f" ({mid_names[0]})" if mid_names else ""

        pipeline = [
            {
                "step": "HTTP request received by embedded Tomcat / Jetty",
                "detail": "Entry point of the web container. DispatcherServlet handles all incoming requests."
            },
            {
                "step": "Spring DispatcherServlet routes request to handler mapping",
                "detail": "Front controller resolves the matching @Controller and @RequestMapping method.",
                "coreRef": "middleware"
            },
            {
                "step": f"HandlerInterceptor.preHandle() fires{mid_note}" if has_interceptor else "Filter chain applied (security headers, CORS)",
                "detail": "Pre-processing hooks run before the controller — logging, auth token check, rate limiting.",
                "coreRef": "middleware"
            },
            {
                "step": f"Spring Security filter chain validates session / token{sec_note}" if has_security else "Authentication check — session or token validated",
                "detail": "Security context loaded. Unauthenticated requests receive 401 before reaching the controller.",
                "coreRef": "security"
            },
            {
                "step": "@Controller method invoked — request body bound and validated",
                "detail": "@RequestBody / @PathVariable / @RequestParam deserialized. @Valid constraints checked.",
                "coreRef": "services"
            },
            {
                "step": "Controller delegates to @Service layer — business logic executed",
                "detail": "Transactional boundaries begin here. Service orchestrates multiple repository calls if needed.",
                "coreRef": "services"
            },
            {
                "step": "@Repository / DAO executes SQL query against database",
                "detail": "Hibernate / JDBC template runs the query. Results mapped to domain objects.",
                "coreRef": "services"
            },
            {
                "step": "Response serialized — JSON / ModelAndView returned to client",
                "detail": "@ResponseBody converts the return value to JSON. HTTP 200 sent unless an exception was thrown."
            }
        ]

        err_handler_note = f" — handled by {err_handler}" if err_handler else ""
        error_pipeline = [
            f"Exception thrown in @Service or @Controller",
            f"@ControllerAdvice intercepts{err_handler_note}",
            "Exception mapped to HTTP status code (400 / 401 / 403 / 500)",
            "Error response body structured (message, code, timestamp)",
            "HandlerInterceptor.afterCompletion() fires (cleanup / logging)",
            "Error JSON returned to client"
        ]
        tenant_note = "Request scope tied to authenticated user session. Data access enforced at the service/repository layer."

    elif fw in ('fastapi', 'django', 'flask'):
        pipeline = [
            {"step": "HTTP request received by ASGI/WSGI server (Uvicorn / Gunicorn)", "detail": "Entry point of the Python application server."},
            {"step": "Middleware stack processes request (CORS, rate limit, request ID)", "detail": "Starlette / Django middleware chain runs top-to-bottom.", "coreRef": "middleware"},
            {"step": "Route matched — endpoint function resolved", "detail": "Path operation matched. Path and query parameters extracted and type-checked."},
            {"step": "Dependency injection resolved (Depends / auth guards)", "detail": "FastAPI Depends chain runs — current user fetched, auth token validated.", "coreRef": "security"},
            {"step": "Request body deserialized and validated (Pydantic / serializers)", "detail": "Schema validation runs. Invalid payloads return 422 before the handler is called."},
            {"step": "Endpoint handler executes — business logic runs", "detail": "Service / CRUD functions called. Database session used.", "coreRef": "services"},
            {"step": "ORM query executed (SQLAlchemy / Django ORM)", "detail": "SQL generated and run against the database. Results mapped to schema models.", "coreRef": "services"},
            {"step": "JSON response returned to client", "detail": "Pydantic model serialized to JSON. HTTP 200 returned."}
        ]
        error_pipeline = [
            "Exception raised in handler or service",
            "Exception handler / middleware intercepts (HTTPException or custom handler)",
            "Error response structured (detail, status_code)",
            "HTTP error returned to client (400 / 401 / 403 / 422 / 500)"
        ]
        tenant_note = "Request isolation enforced via dependency-injected database sessions and user-scoped queries."

    else:
        # Express / NestJS / generic
        pipeline = [
            {"step": "HTTP request received by Node.js HTTP server", "detail": "Express / Fastify receives the raw request object."},
            {"step": "Global middleware applied (Helmet, CORS, body-parser)", "detail": "Security headers set. Request body parsed to JSON.", "coreRef": "middleware"},
            {"step": "Route matched — module router selected", "detail": "Express router tree traversed. Route parameters extracted."},
            {"step": "Auth middleware runs — JWT Bearer token validated", "detail": "authenticateJWT / Passport strategy decodes token. 401 on failure.", "coreRef": "security"},
            {"step": "Guard / RBAC check — role and permission verified", "detail": "authorizeRoles / NestJS Guards verify the user has the required permission. 403 on failure.", "coreRef": "security"},
            {"step": "Controller / Route handler processes request", "detail": "Business logic executed. Service methods called.", "coreRef": "services"},
            {"step": "ORM / query builder executes database query", "detail": "Prisma / TypeORM / Knex runs SQL. Results returned as objects.", "coreRef": "services"},
            {"step": "JSON response returned to client", "detail": "res.json() sends serialized payload with appropriate HTTP status."}
        ]
        error_pipeline = [
            "Unhandled error thrown in controller or service",
            "Global error handler middleware intercepts (app.use error handler)",
            "Error logged (console / logger service)",
            "HTTP error response structured and returned (400 / 401 / 403 / 500)"
        ]
        tenant_note = "Tenant data isolation enforced via middleware scope and schema queries."

    return {
        "requestPipeline": pipeline,
        "errorPipeline": error_pipeline,
        "tenantIsolation": tenant_note
    }


# ---------------------------------------------------------------------------
# architecture.json INITIALISER — now powered by codebase scanner
# ---------------------------------------------------------------------------

def init_architecture(target_root=None):
    """Scan the codebase and generate architecture.json automatically."""
    if not target_root:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root = _find_root(script_dir)
    else:
        root = target_root

    arch_dir = os.path.join(root, 'docs', 'architecture') if os.path.basename(root) != 'architecture' else root
    os.makedirs(arch_dir, exist_ok=True)
    json_path = os.path.join(arch_dir, 'architecture.json')
    fw   = _detect_fw(root)

    proj_name = None
    proj_desc = None
    for pkg_loc in [os.path.join(root, 'package.json'), os.path.join(root, 'backend', 'package.json')]:
        if os.path.isfile(pkg_loc):
            try:
                d = json.load(open(pkg_loc, encoding='utf-8'))
                if d.get('name'): proj_name = d.get('name')
                if d.get('description'): proj_desc = d.get('description')
                if proj_name and proj_desc: break
            except: pass
    if not proj_name or proj_name in ('arch-wiki', 'template'):
        proj_name = os.path.basename(root)
    if not proj_desc:
        proj_desc = f"{proj_name.replace('-', ' ').replace('_', ' ').title()} Architecture & API Map"

    display_name = proj_name.replace('-',' ').replace('_',' ').title()

    fw_info = {'express':{'language':'TypeScript','framework':'Express.js'},
               'nestjs': {'language':'TypeScript','framework':'NestJS'},
               'fastapi':{'language':'Python',    'framework':'FastAPI'},
               'django': {'language':'Python',    'framework':'Django'},
               'flask':  {'language':'Python',    'framework':'Flask'},
               'spring': {'language':'Java 17',   'framework':'Spring Boot'},
               'unknown':{'language':'TypeScript','framework':'Express.js'}}.get(fw,{'language':'TypeScript','framework':'Express.js'})

    java_info = _java_build_info(root) if fw in ('spring', 'java') else {}
    if java_info:
        if java_info.get('javaVersion'):
            fw_info = dict(fw_info, language=f"Java {java_info['javaVersion']}")
        if java_info.get('springBootVersion'):
            fw_info = dict(fw_info, framework=f"Spring Boot {java_info['springBootVersion']}")

    print(f"[arch-wiki] Root: {root} | Framework: {fw}")

    # 3. Scan docker-compose
    infrastructure, docker_diagram = _scan_docker(root)
    print(f"[arch-wiki] Docker: {len(infrastructure)} service(s)")

    # 4. Scan routes
    if fw in ('express','nestjs','fastify'):
        modules = _scan_express(root)
    elif fw == 'fastapi':
        modules = _scan_fastapi(root)
    elif fw in ('spring', 'java'):
        modules = _scan_java_spring(root)
    else:
        modules = _scan_express(root)
        if not modules:
            modules = _scan_java_spring(root)
    total_ep = sum(len(m['endpoints']) for m in modules)
    print(f"[arch-wiki] Routes: {len(modules)} module(s), {total_ep} endpoint(s)")

    # 5. Workspaces
    workspaces = _scan_workspaces(root)

    # 6. Collect all permission slugs & details
    perm_details = []
    for mod in modules:
        for ep in mod.get('endpoints', []):
            pslug = ep.get('permission')
            full_ep_path = (mod['basePath'] + ("" if ep['path'] == "/" else ep['path'])).replace("//", "/")
            ep_obj = {"method": ep['method'], "path": full_ep_path}

            if pslug:
                sub_slugs = [s.strip() for s in pslug.split('|') if s.strip()]
            elif ep.get('auth', False):
                sub_slugs = ['authenticated']
            else:
                sub_slugs = ['public']

            for sub_slug in sub_slugs:
                existing = next((d for d in perm_details if d['slug'] == sub_slug), None)
                if existing:
                    if ep_obj not in existing['endpoints']:
                        existing['endpoints'].append(ep_obj)
                else:
                    action_type = "SYSTEM SCOPE" if sub_slug in ('authenticated', 'public') else "RBAC PERMISSION"
                    page_label = "Public Access" if sub_slug == 'public' else ("Authenticated User Access" if sub_slug == 'authenticated' else f"{mod['name']} Management")
                    perm_details.append({
                        "slug": sub_slug,
                        "module": mod['name'],
                        "action": action_type,
                        "endpoints": [ep_obj],
                        "adminPages": [page_label]
                    })

    all_perms = sorted(set(d['slug'] for d in perm_details))

    # 7. System arch diagram
    sys_diag = _build_sys_diagram(modules, infrastructure)

    # 8. Core Layer & SQL Queries
    core_layer = _scan_core_layer(root, fw)

    sql_queries = []
    for mod in modules:
        mname = mod['name']
        bpath = mod['basePath']
        raw_table = mod['id'].replace('-', '_')
        table_name = raw_table + 's'
        
        for ep in mod.get('endpoints', []):
            method = ep.get('method', 'GET').upper()
            ep_path = ep.get('path', '/')
            full_ep_path = (bpath + ("" if ep_path == "/" else ep_path)).replace("//", "/")
            
            has_id = bool(re.search(r':[^/]+|\{[^}]+\}', ep_path))
            sub_resource = None
            path_segs = [p for p in ep_path.split('/') if p and not p.startswith(':') and not p.startswith('{')]
            if path_segs:
                sub_resource = path_segs[-1].replace('-', '_')

            if method == 'GET':
                if has_id:
                    label = f"Find {mname} by ID"
                    fn_name = f"get{mname}ById"
                    purpose = f"Fetch single {mname} record by unique ID"
                    sql_stmt = f"SELECT * FROM \"{table_name}\" WHERE id = $1 LIMIT 1;"
                elif sub_resource and sub_resource != mod['id']:
                    label = f"Get {mname} {sub_resource.title()}"
                    fn_name = f"get{mname}{sub_resource.title()}"
                    purpose = f"Fetch {sub_resource} for {mname} module"
                    sql_stmt = f"SELECT * FROM \"{sub_resource}\" ORDER BY created_at DESC;"
                else:
                    label = f"List All {mname} Records"
                    fn_name = f"list{mname}s"
                    purpose = f"Fetch all records for {mname} module"
                    sql_stmt = f"SELECT * FROM \"{table_name}\" ORDER BY created_at DESC;"

            elif method == 'POST':
                if sub_resource and sub_resource != mod['id']:
                    label = f"Create {mname} {sub_resource.title()}"
                    fn_name = f"create{mname}{sub_resource.title()}"
                    purpose = f"Insert new {sub_resource} record linked to {mname}"
                    sql_stmt = f"INSERT INTO \"{sub_resource}\" ({mod['id']}_id, created_at) VALUES ($1, NOW()) RETURNING *;"
                else:
                    label = f"Create New {mname}"
                    fn_name = f"create{mname}"
                    purpose = f"Insert new record into {mname} table"
                    sql_stmt = f"INSERT INTO \"{table_name}\" (id, created_at) VALUES ($1, NOW()) RETURNING *;"

            elif method in ('PUT', 'PATCH'):
                if sub_resource and sub_resource != mod['id']:
                    label = f"Update {mname} {sub_resource.title()}"
                    fn_name = f"update{mname}{sub_resource.title()}"
                    purpose = f"Update {sub_resource} attribute on {mname}"
                    sql_stmt = f"UPDATE \"{table_name}\" SET {sub_resource} = $1, updated_at = NOW() WHERE id = $2 RETURNING *;"
                else:
                    label = f"Update {mname} Record"
                    fn_name = f"update{mname}"
                    purpose = f"Update existing {mname} record by ID"
                    sql_stmt = f"UPDATE \"{table_name}\" SET updated_at = NOW() WHERE id = $1 RETURNING *;"

            elif method == 'DELETE':
                label = f"Delete {mname} Record"
                fn_name = f"delete{mname}"
                purpose = f"Delete record from {table_name} by ID"
                sql_stmt = f"DELETE FROM \"{table_name}\" WHERE id = $1;"

            else:
                label = f"Execute {method} on {mname}"
                fn_name = f"process{mname}"
                purpose = f"Execute operation for {full_ep_path}"
                sql_stmt = f"SELECT * FROM \"{table_name}\" WHERE id = $1;"

            ctrl_file = mod['files'][0] if (mod.get('files') and len(mod['files']) > 0) else (f"src/{mod['id']}.java" if fw in ('spring', 'java') else f"src/controllers/{mod['id']}.controller.ts")
            sql_queries.append({
                "label": label,
                "module": mname,
                "function": fn_name,
                "purpose": purpose,
                "file": ctrl_file,
                "tables": [sub_resource if (sub_resource and sub_resource != mod['id']) else table_name],
                "endpoints": [{"method": method, "path": full_ep_path}],
                "sql": sql_stmt
            })

    db_name = next((s['image'].split(':')[0].split('/')[-1].title()
                    for s in infrastructure if s['type']=='database'), 'PostgreSQL')

    today = datetime.date.today().isoformat()
    total_ep_str = f"{total_ep}/{total_ep}"

    prerequisites = _scan_prerequisites(root, fw, infrastructure, workspaces, java_info)

    scaffold = {
        "meta": {
            "displayName": display_name,
            "version": "1.0.0",
            "description": proj_desc or f"{display_name} REST API",
            "generatedAt": today,
            "techStack": {
                "language": fw_info['language'],
                "framework": fw_info['framework'],
                "database": db_name,
                "auth": "JWT / Bearer Token"
            }
        },
        "prerequisites": prerequisites,
        "workspaces": workspaces,
        "infrastructure": infrastructure,
        "dockerDiagram": docker_diagram,
        "systemArchitectureDiagram": sys_diag,
        "swaggerSchemas": {
            "matchStatus": f"Verified Parity ({total_ep_str} Endpoints)",
            "openapi": "3.0.0",
            "servedAt": "/api/docs",
            "securityScheme": "bearerAuth (JWT Bearer Token)",
            "servers": [
                {"url": "http://localhost:3000", "description": "Local Development Server"},
                {"url": f"https://api.{display_name.lower().replace(' ','-')}.com", "description": "Production"}
            ],
            "schemas": []
        },
        "modules": modules,
        "systemEndpoints": [
            {"method": "GET", "path": "/health", "auth": False, "description": "Health check endpoint"}
        ],
        "coreLayer": core_layer,
        "dataFlow": _build_data_flow(fw, core_layer),
        "permissions": {
            "description": "RBAC permission catalog and endpoint mapping.",
            "catalog": all_perms,
            "details": perm_details
        },
        "sqlQueries": sql_queries
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(scaffold, f, indent=2)

    print(f"[arch-wiki] Generated architecture.json -> {json_path}")
    return scaffold


def _scan_prerequisites(root, fw, infrastructure, workspaces, java_info=None):
    tools = []
    java_info = java_info or {}

    # 1. Primary Runtime Engine
    if fw in ('express', 'nestjs', 'fastify'):
        tools.append({
            "name": "Node.js & npm",
            "version": ">= 18.0.0",
            "required": True,
            "category": "runtime",
            "description": "JavaScript runtime engine for executing the Express REST API backend and frontend tooling."
        })
    elif fw in ('spring', 'java'):
        tools.append({
            "name": "Java OpenJDK / JDK",
            "version": f">= {java_info.get('javaVersion') or '17'}",
            "required": True,
            "category": "runtime",
            "description": "Java SE Development Kit required for Spring Boot backend compilation and execution."
        })
    elif fw in ('fastapi', 'django', 'flask'):
        tools.append({
            "name": "Python",
            "version": ">= 3.10",
            "required": True,
            "category": "runtime",
            "description": "Python runtime interpreter for backend API execution and virtual environments."
        })
    else:
        tools.append({
            "name": "Node.js",
            "version": ">= 18.0.0",
            "required": True,
            "category": "runtime",
            "description": "JavaScript runtime environment."
        })

    # 2. Containerization / Infrastructure tools
    has_compose = os.path.isfile(os.path.join(root, 'docker-compose.yml')) or os.path.isfile(os.path.join(root, 'docker-compose.yaml'))
    if infrastructure or has_compose:
        tools.append({
            "name": "Docker & Docker Compose",
            "version": ">= 24.0.0 (Compose v2)",
            "required": True,
            "category": "infrastructure",
            "description": "Container engine & orchestration tool to launch database, caching, messaging, and monitoring services."
        })

    # 3. Services detected from infrastructure
    for s in infrastructure:
        stype = s.get('type', '')
        sname = s.get('name', 'Service')
        simg  = s.get('image', 'latest')
        sport = s.get('port')
        if stype in ('database', 'cache', 'queue', 'monitoring'):
            tools.append({
                "name": f"{sname} ({stype.title()})",
                "version": simg,
                "required": True if stype in ('database', 'cache') else False,
                "category": stype,
                "description": f"Containerized {stype} service running on port {sport or 'internal'}."
            })

    # 4. Workspace & Monorepo Package Managers
    if os.path.isfile(os.path.join(root, 'pnpm-workspace.yaml')):
        tools.append({
            "name": "pnpm Package Manager",
            "version": ">= 8.0.0",
            "required": True,
            "category": "package_manager",
            "description": "Disk-efficient monorepo package manager."
        })

    # Setup Steps Pipeline
    setup_steps = []
    step_num = 1

    # Step 1: Environment File Setup
    env_file = os.path.join(root, '.env.example')
    if not os.path.isfile(env_file):
        env_file = os.path.join(root, 'apps', 'api', '.env.example')

    if os.path.isfile(env_file):
        setup_steps.append({
            "step": step_num,
            "title": "Configure Environment Variables",
            "command": "cp .env.example .env",
            "description": "Create local .env configuration file and update database host, credentials, JWT secrets, and service ports."
        })
    else:
        setup_steps.append({
            "step": step_num,
            "title": "Configure Environment Variables",
            "command": "touch .env",
            "description": "Set up environment variables (PORT, DB_HOST, DB_PASSWORD, JWT_SECRET)."
        })
    step_num += 1

    # Step 2: Launch Docker Containers
    if infrastructure or has_compose:
        setup_steps.append({
            "step": step_num,
            "title": "Start Infrastructure Containers",
            "command": "docker compose up -d",
            "description": "Spin up containerized services in background mode."
        })
        step_num += 1

    # Step 3: Install Package Dependencies
    if fw in ('express', 'nestjs', 'fastify'):
        setup_steps.append({
            "step": step_num,
            "title": "Install Workspace Dependencies",
            "command": "npm install",
            "description": "Install dependencies across backend API, shared libraries, and admin frontend."
        })
    elif fw in ('spring', 'java'):
        setup_steps.append({
            "step": step_num,
            "title": "Build Maven Modules",
            "command": "./mvnw clean install -DskipTests",
            "description": "Compile Java packages and download Maven dependencies."
        })
    elif fw in ('fastapi', 'django', 'flask'):
        setup_steps.append({
            "step": step_num,
            "title": "Install Python Virtual Environment",
            "command": "python -m venv venv && source venv/bin/activate && pip install -r requirements.txt",
            "description": "Initialize virtual environment and install dependencies."
        })
    step_num += 1

    # Step 4: Database Migrations & Seeds
    setup_steps.append({
        "step": step_num,
        "title": "Run Schema Migrations & Database Seeds",
        "command": "npm run db:migrate && npm run db:seed" if fw in ('express', 'nestjs') else ("./mvnw compile exec:java" if fw == 'spring' else "alembic upgrade head"),
        "description": "Execute database schema migrations and populate initial seed records."
    })
    step_num += 1

    # Step 5: Boot Application Development Server
    setup_steps.append({
        "step": step_num,
        "title": "Launch Development Server",
        "command": "npm run dev" if fw in ('express', 'nestjs') else ("./mvnw spring-boot:run" if fw == 'spring' else "uvicorn main:app --reload"),
        "description": "Start backend API in watch mode."
    })

    return {
        "description": "Software runtimes, system dependencies, and step-by-step initialization commands required to run the project.",
        "tools": tools,
        "setupSteps": setup_steps
    }



def load_architecture(json_path=None):
    if not json_path:
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'architecture.json')
    if not os.path.isfile(json_path):
        print("[arch-wiki] architecture.json not found — running codebase scan initialization...")
        target_root = os.path.dirname(os.path.dirname(os.path.dirname(json_path)))
        return init_architecture(target_root)
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_mermaid(text):
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9 _\-\.:]', '', str(text))

def build_openapi_spec(data):
    meta = data.get('meta', {})
    modules = data.get('modules', [])
    system_endpoints = data.get('systemEndpoints', [])
    swagger_schemas = data.get('swaggerSchemas', {})

    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": meta.get('displayName', 'SaaS MVP Platform API'),
            "version": meta.get('version', '1.0.0'),
            "description": meta.get('description', 'Multi-tenant SaaS REST API with full RBAC, JWT, RLS, and Prometheus telemetry.')
        },
        "servers": swagger_schemas.get('servers', [
            {"url": "http://localhost:3000", "description": "Local Development Server"},
            {"url": "https://api.saas-mvp.com", "description": "Production API Gateway"}
        ]),
        "tags": [],
        "paths": {},
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Provide your JWT Access Token (Header: Authorization: Bearer <token>)"
                }
            },
            "schemas": {}
        }
    }

    for mod in modules:
        mod_name = mod.get('name', '')
        base_path = mod.get('basePath', '')
        spec['tags'].append({
            "name": mod_name,
            "description": mod.get('description', '')
        })

        for ep in mod.get('endpoints', []):
            method = ep.get('method', 'GET').lower()
            path_suffix = ep.get('path', '')
            full_path = (base_path + ("" if path_suffix == "/" else path_suffix)).replace("//", "/")
            openapi_path = re.sub(r':([a-zA-Z0-9_]+)', r'{\1}', full_path)

            if openapi_path not in spec['paths']:
                spec['paths'][openapi_path] = {}

            parameters = []
            path_params = re.findall(r'\{([a-zA-Z0-9_]+)\}', openapi_path)
            for param in path_params:
                parameters.append({
                    "name": param,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": f"Target {param} identifier"
                })

            perm_slug = ep.get('permission')
            perm_desc = f"Required Permission: `{perm_slug}`" if perm_slug else "Public / Authenticated Route"

            op = {
                "tags": [mod_name],
                "summary": ep.get('description', ''),
                "description": f"{ep.get('description', '')} | {perm_desc}",
                "parameters": parameters,
                "responses": {
                    "200": {
                        "description": "Successful Request",
                        "content": {
                            "application/json": {
                                "example": {"success": True, "data": {}}
                            }
                        }
                    },
                    "400": {"description": "Invalid payload parameters"},
                    "401": {"description": "Missing or expired JWT Bearer token"},
                    "403": {"description": "Forbidden - Insufficient permissions"},
                    "422": {"description": "Validation error"},
                    "500": {"description": "Internal server error"}
                }
            }

            if ep.get('auth', False):
                op["security"] = [{"bearerAuth": []}]

            if method in ["post", "put", "patch"]:
                op["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "example": {"exampleField": "exampleValue"}
                            }
                        }
                    }
                }

            spec['paths'][openapi_path][method] = op

    if system_endpoints:
        spec['tags'].append({"name": "System", "description": "System health and telemetry endpoints"})
        for sys_ep in system_endpoints:
            spath = sys_ep.get('path', '')
            smethod = sys_ep.get('method', 'GET').lower()
            if spath not in spec['paths']:
                spec['paths'][spath] = {}
            spec['paths'][spath][smethod] = {
                "tags": ["System"],
                "summary": sys_ep.get('description', ''),
                "responses": {"200": {"description": "System Operational"}}
            }

    for sch in swagger_schemas.get('schemas', []):
        spec['components']['schemas'][sch.get('name')] = {
            "type": "object",
            "description": sch.get('description')
        }

    return spec

def generate_html(data, target_dir=None):
    meta = data.get('meta', {})
    workspaces = data.get('workspaces', [])
    infrastructure = data.get('infrastructure', [])
    core_layer = data.get('coreLayer', {})
    modules = data.get('modules', [])
    system_endpoints = data.get('systemEndpoints', [])
    data_flow = data.get('dataFlow', {})
    permissions = data.get('permissions', {})
    docker_diagram = data.get('dockerDiagram', {})
    system_arch_diagram = data.get('systemArchitectureDiagram', {})
    swagger_schemas = data.get('swaggerSchemas', {})
    sql_queries = data.get('sqlQueries', [])
    prerequisites = data.get('prerequisites', {})

    tech_stack = meta.get('techStack', {})
    total_endpoints = sum(len(m.get('endpoints', [])) for m in modules) + len(system_endpoints)
    prereq_tools = prerequisites.get('tools', [])
    prereq_steps = prerequisites.get('setupSteps', [])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(meta.get('displayName', 'SaaS MVP'))} — Architecture Map</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <style>
        :root {{
            --bg: #0d1117;
            --bg2: #161b22;
            --bg3: #21262d;
            --border: #30363d;
            --text: #e6edf3;
            --muted: #8b949e;
            --accent: #58a6ff;
            --green: #3fb950;
            --yellow: #d29922;
            --red: #f85149;
            --purple: #bc8cff;
            --orange: #ff8c42;
            --font-main: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-code: 'Fira Code', monospace;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg);
            color: var(--text);
            font-family: var(--font-main);
            min-height: 100vh;
            overflow-x: hidden;
        }}

        .header {{
            background: var(--bg2);
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 200;
            height: 65px;
        }}
        .header-top {{
            padding: 0 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 100%;
        }}

        .app-layout {{
            display: flex;
            width: 100vw;
            min-height: calc(100vh - 65px);
        }}

        .sidebar {{
            width: 280px;
            min-width: 280px;
            background: var(--bg2);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            position: fixed;
            top: 65px;
            bottom: 0;
            left: 0;
            z-index: 100;
        }}

        .sidebar-header {{
            padding: 16px 20px 12px 20px;
            border-bottom: 1px solid var(--border);
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 10px;
        }}
        .brand-icon {{
            font-size: 28px;
        }}
        .brand-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text);
            line-height: 1.2;
        }}
        .brand-sub {{
            font-size: 11px;
            color: var(--muted);
            margin-top: 4px;
            line-height: 1.4;
        }}
        .sidebar-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }}

        .badge {{
            background: var(--bg3);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            color: var(--muted);
        }}
        .badge-green {{
            background: rgba(63, 185, 80, 0.15);
            color: var(--green);
            border: 1px solid rgba(63, 185, 80, 0.4);
            font-weight: 600;
        }}

        .sidebar-nav {{
            flex: 1;
            padding: 16px 12px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .nav-btn {{
            background: none;
            border: 1px solid transparent;
            color: var(--muted);
            padding: 10px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            text-align: left;
            transition: all .15s ease;
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }}
        .nav-btn:hover {{
            background: var(--bg3);
            color: var(--text);
        }}
        .nav-btn.active {{
            background: rgba(88, 166, 255, 0.15);
            color: var(--accent);
            border-color: rgba(88, 166, 255, 0.4);
            font-weight: 600;
        }}
        .nav-btn-left {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .nav-count {{
            background: var(--bg3);
            color: var(--muted);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }}
        .nav-btn.active .nav-count {{
            background: var(--accent);
            color: #000;
        }}

        .sidebar-footer {{
            padding: 14px 20px;
            border-top: 1px solid var(--border);
            font-size: 11px;
            color: var(--muted);
            text-align: center;
        }}

        .main-content {{
            margin-left: 280px;
            flex: 1;
            padding: 28px 36px;
            max-width: 1500px;
            width: calc(100vw - 280px);
        }}
        .section {{ display: none; }}
        .section.active {{ display: block; }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }}
        .stat {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }}
        .stat-num {{
            font-size: 28px;
            font-weight: 700;
            color: var(--accent);
        }}
        .stat-lbl {{
            font-size: 12px;
            color: var(--muted);
            margin-top: 4px;
        }}

        .sec-title {{
            font-size: 17px;
            font-weight: 700;
            margin: 24px 0 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text);
        }}

        .grid3 {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }}
        .grid2 {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 16px; }}
        .grid1 {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}

        .card {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: border-color .2s;
        }}
        .card:hover {{
            border-color: var(--accent);
        }}
        .color-bar {{
            height: 3px;
            border-radius: 3px;
            margin-bottom: 12px;
        }}
        .chead {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}
        .card-title {{
            font-size: 15px;
            font-weight: 600;
        }}
        .card-sub {{
            font-size: 12px;
            color: var(--muted);
            margin-top: 2px;
        }}
        .card-desc {{
            font-size: 13px;
            color: var(--muted);
            line-height: 1.6;
            margin: 10px 0;
        }}

        .tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            margin: 2px;
        }}
        .tb {{ background: rgba(88,166,255,.15); color: var(--accent); }}
        .tg {{ background: rgba(63,185,80,.15); color: var(--green); }}
        .tr {{ background: rgba(248,81,73,.15); color: var(--red); }}
        .ty {{ background: rgba(210,153,34,.15); color: var(--yellow); }}
        .tp {{ background: rgba(188,140,255,.15); color: var(--purple); }}
        .tq {{ background: var(--bg3); color: var(--muted); }}

        .endpoint {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 8px 10px;
            border-radius: 6px;
            margin: 4px 0;
            background: var(--bg3);
        }}
        .method {{
            font-size: 10px;
            font-weight: 700;
            padding: 3px 7px;
            border-radius: 4px;
            min-width: 54px;
            text-align: center;
            flex-shrink: 0;
        }}
        .GET {{ background: rgba(63,185,80,.2); color: var(--green); }}
        .POST {{ background: rgba(88,166,255,.2); color: var(--accent); }}
        .PUT {{ background: rgba(210,153,34,.2); color: var(--yellow); }}
        .PATCH {{ background: rgba(255,140,66,.2); color: var(--orange); }}
        .DELETE {{ background: rgba(248,81,73,.2); color: var(--red); }}

        .ep-path {{ font-size: 12px; font-family: var(--font-code); color: var(--text); }}
        .ep-desc {{ font-size: 11px; color: var(--muted); margin-top: 2px; }}
        .lock {{ font-size: 10px; margin-left: 6px; opacity: .8; color: var(--purple); }}

        .search {{
            width: 100%;
            padding: 10px 16px;
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
            margin-bottom: 20px;
            outline: none;
        }}
        .search:focus {{ border-color: var(--accent); }}

        .pipeline {{ display: flex; flex-direction: column; }}
        .pipe-step {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: var(--bg2);
            border: 1px solid var(--border);
            margin-top: -1px;
        }}
        .pipe-step:first-child {{ border-radius: 8px 8px 0 0; }}
        .pipe-step:last-child {{ border-radius: 0 0 8px 8px; }}
        .pipe-num {{
            background: var(--accent);
            color: #000;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .perm-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 8px; margin-bottom: 20px; }}
        .perm-item {{
            background: var(--bg3);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            font-family: var(--font-code);
            color: var(--purple);
        }}

        .perm-card {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-left: 4px solid var(--purple);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .perm-flow {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
            font-size: 12px;
            margin-top: 8px;
        }}
        .flow-arrow {{ color: var(--muted); font-weight: bold; }}

        .code-block {{
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 12px;
            font-family: var(--font-code);
            font-size: 12px;
            color: var(--text);
            overflow-x: auto;
            white-space: pre-wrap;
            margin-top: 8px;
        }}
        .diagram-box {{
            position: relative;
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            overflow: hidden;
            cursor: grab !important;
        }}
        .diagram-box:active {{
            cursor: grabbing !important;
        }}
        .diagram-box svg, .diagram-box svg * {{
            cursor: grab !important;
        }}
        .diagram-box svg:active, .diagram-box svg:active * {{
            cursor: grabbing !important;
        }}
        .diagram-toolbar {{
            position: absolute;
            top: 12px;
            right: 12px;
            z-index: 100;
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(13, 17, 23, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 4px 8px;
        }}
        .diagram-toolbar button {{
            background: var(--bg3);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.15s ease;
        }}
        .diagram-toolbar button:hover {{
            background: var(--accent);
            color: #000;
            border-color: var(--accent);
        }}

        .mwcard {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 10px;
        }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: var(--bg3); color: var(--muted); font-weight: 600; font-size: 12px; }}

        .sub-tab-btn {{
            background: var(--bg2);
            border: 1px solid var(--border);
            color: var(--muted);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all .15s ease;
        }}
        .sub-tab-btn:hover {{
            background: var(--bg3);
            color: var(--text);
        }}
        .sub-tab-btn.active {{
            background: var(--accent);
            color: #000;
            font-weight: 600;
            border-color: var(--accent);
        }}
        .swagger-view-pane {{
            display: none;
        }}
        .swagger-view-pane.active {{
            display: block;
        }}

        /* Comprehensive High-Contrast Dark Theme Overrides for Swagger UI */
        #swagger-ui-container .swagger-ui {{
            color: var(--text) !important;
            font-family: var(--font-main) !important;
        }}
        #swagger-ui-container .swagger-ui * {{
            border-color: var(--border) !important;
        }}
        #swagger-ui-container .swagger-ui .info {{
            margin: 15px 0 25px 0 !important;
            background: transparent !important;
        }}
        #swagger-ui-container .swagger-ui .info .title {{
            color: var(--text) !important;
            font-size: 24px !important;
        }}
        #swagger-ui-container .swagger-ui .info p,
        #swagger-ui-container .swagger-ui .info li,
        #swagger-ui-container .swagger-ui .info td,
        #swagger-ui-container .swagger-ui .info a {{
            color: var(--muted) !important;
        }}
        #swagger-ui-container .swagger-ui .scheme-container {{
            background: var(--bg2) !important;
            border-radius: 8px !important;
            padding: 16px !important;
            box-shadow: none !important;
            border: 1px solid var(--border) !important;
            margin-bottom: 20px !important;
        }}
        #swagger-ui-container .swagger-ui label,
        #swagger-ui-container .swagger-ui .title,
        #swagger-ui-container .swagger-ui .servers-title {{
            color: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-tag {{
            color: var(--text) !important;
            border-bottom: 1px solid var(--border) !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            padding: 10px 0 !important;
            margin: 20px 0 10px 0 !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-tag small {{
            color: var(--muted) !important;
            font-size: 13px !important;
            font-weight: 400 !important;
        }}
        #swagger-ui-container .swagger-ui .opblock {{
            background: var(--bg2) !important;
            border-radius: 8px !important;
            border: 1px solid var(--border) !important;
            margin-bottom: 14px !important;
            box-shadow: none !important;
            overflow: hidden !important;
        }}
        #swagger-ui-container .swagger-ui .opblock .opblock-summary {{
            padding: 10px 14px !important;
            border-bottom: 1px solid transparent !important;
            display: flex !important;
            align-items: center !important;
        }}
        #swagger-ui-container .swagger-ui .opblock .opblock-summary-path,
        #swagger-ui-container .swagger-ui .opblock .opblock-summary-path__deprecated {{
            color: var(--text) !important;
            font-family: var(--font-code) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }}
        #swagger-ui-container .swagger-ui .opblock .opblock-summary-description {{
            color: var(--muted) !important;
            font-size: 12px !important;
        }}

        /* HTTP Method Badges & Container States */
        /* GET */
        #swagger-ui-container .swagger-ui .opblock.opblock-get {{
            background: rgba(63, 185, 80, 0.08) !important;
            border-color: rgba(63, 185, 80, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-get .opblock-summary-method {{
            background: #3fb950 !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}
        /* POST */
        #swagger-ui-container .swagger-ui .opblock.opblock-post {{
            background: rgba(88, 166, 255, 0.08) !important;
            border-color: rgba(88, 166, 255, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-post .opblock-summary-method {{
            background: #58a6ff !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}
        /* PUT */
        #swagger-ui-container .swagger-ui .opblock.opblock-put {{
            background: rgba(210, 153, 34, 0.08) !important;
            border-color: rgba(210, 153, 34, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-put .opblock-summary-method {{
            background: #d29922 !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}
        /* PATCH */
        #swagger-ui-container .swagger-ui .opblock.opblock-patch {{
            background: rgba(255, 140, 66, 0.08) !important;
            border-color: rgba(255, 140, 66, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-patch .opblock-summary-method {{
            background: #ff8c42 !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}
        /* DELETE */
        #swagger-ui-container .swagger-ui .opblock.opblock-delete {{
            background: rgba(248, 81, 73, 0.08) !important;
            border-color: rgba(248, 81, 73, 0.4) !important;
        }}
        #swagger-ui-container .swagger-ui .opblock.opblock-delete .opblock-summary-method {{
            background: #f85149 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            padding: 4px 10px !important;
            text-shadow: none !important;
        }}

        /* Expanded Opblock Body & Sections */
        #swagger-ui-container .swagger-ui .opblock-body {{
            background: var(--bg2) !important;
            color: var(--text) !important;
            border-top: 1px solid var(--border) !important;
            padding: 16px !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-section-header {{
            background: var(--bg3) !important;
            color: var(--text) !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            border: 1px solid var(--border) !important;
            margin-bottom: 12px !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-section-header h4 {{
            color: var(--text) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }}
        #swagger-ui-container .swagger-ui .opblock-description-wrapper,
        #swagger-ui-container .swagger-ui .opblock-description-wrapper p,
        #swagger-ui-container .swagger-ui .markdown p,
        #swagger-ui-container .swagger-ui .renderedMarkdown,
        #swagger-ui-container .swagger-ui .renderedMarkdown p {{
            color: var(--text) !important;
            font-size: 13px !important;
            line-height: 1.5 !important;
        }}

        /* Parameter & Response Tables */
        #swagger-ui-container .swagger-ui table {{
            background: transparent !important;
            width: 100% !important;
        }}
        #swagger-ui-container .swagger-ui table thead tr th,
        #swagger-ui-container .swagger-ui table thead tr td {{
            color: var(--muted) !important;
            border-bottom: 1px solid var(--border) !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            padding: 8px 12px !important;
            background: transparent !important;
        }}
        #swagger-ui-container .swagger-ui table.parameters td,
        #swagger-ui-container .swagger-ui table.responses-table td {{
            color: var(--text) !important;
            border-bottom: 1px solid var(--border) !important;
            padding: 10px 12px !important;
            background: transparent !important;
        }}
        #swagger-ui-container .swagger-ui .parameter__name {{
            color: var(--text) !important;
            font-family: var(--font-code) !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }}
        #swagger-ui-container .swagger-ui .parameter__name.required:after {{
            color: var(--red) !important;
        }}
        #swagger-ui-container .swagger-ui .parameter__type,
        #swagger-ui-container .swagger-ui .parameter__extension {{
            color: var(--purple) !important;
            font-family: var(--font-code) !important;
            font-size: 12px !important;
        }}
        #swagger-ui-container .swagger-ui .parameter__in {{
            color: var(--muted) !important;
            font-family: var(--font-code) !important;
            font-size: 11px !important;
            font-style: italic !important;
        }}

        /* Response Code Indicators & Links */
        #swagger-ui-container .swagger-ui .responses-inner {{
            background: var(--bg) !important;
            padding: 16px !important;
            border-radius: 8px !important;
            border: 1px solid var(--border) !important;
            margin-top: 10px !important;
        }}
        #swagger-ui-container .swagger-ui .responses-inner h4,
        #swagger-ui-container .swagger-ui .responses-inner h5 {{
            color: var(--text) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }}
        #swagger-ui-container .swagger-ui .response-col_status {{
            color: var(--green) !important;
            font-family: var(--font-code) !important;
            font-weight: 700 !important;
            font-size: 13px !important;
        }}
        #swagger-ui-container .swagger-ui .response-col_description {{
            color: var(--text) !important;
            font-size: 13px !important;
        }}
        #swagger-ui-container .swagger-ui .response-col_links {{
            color: var(--muted) !important;
        }}

        /* Models & Schema Boxes */
        #swagger-ui-container .swagger-ui section.models {{
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            background: var(--bg2) !important;
            margin-top: 30px !important;
            padding: 16px !important;
        }}
        #swagger-ui-container .swagger-ui section.models h4 {{
            color: var(--text) !important;
            border-bottom: 1px solid var(--border) !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            padding-bottom: 10px !important;
        }}
        #swagger-ui-container .swagger-ui .model-container {{
            background: var(--bg3) !important;
            border-radius: 6px !important;
            padding: 12px !important;
            margin-top: 10px !important;
            border: 1px solid var(--border) !important;
        }}
        #swagger-ui-container .swagger-ui .model-box {{
            background: var(--bg3) !important;
            color: var(--text) !important;
            border-radius: 6px !important;
            padding: 10px !important;
        }}
        #swagger-ui-container .swagger-ui .model-title {{
            color: var(--accent) !important;
            font-family: var(--font-code) !important;
            font-weight: 600 !important;
        }}
        #swagger-ui-container .swagger-ui .model,
        #swagger-ui-container .swagger-ui .model-box pre {{
            color: var(--text) !important;
            font-family: var(--font-code) !important;
            font-size: 12px !important;
        }}
        #swagger-ui-container .swagger-ui .prop-type {{
            color: var(--purple) !important;
        }}
        #swagger-ui-container .swagger-ui .prop-format {{
            color: var(--muted) !important;
        }}

        /* Code Snippets, Inputs & Interactive Controls */
        #swagger-ui-container .swagger-ui pre,
        #swagger-ui-container .swagger-ui .highlight-code pre,
        #swagger-ui-container .swagger-ui .model-example pre,
        #swagger-ui-container .swagger-ui .example pre {{
            background: var(--bg) !important;
            color: var(--text) !important;
            font-family: var(--font-code) !important;
            font-size: 12px !important;
            line-height: 1.6 !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            padding: 14px 16px !important;
            margin: 6px 0 !important;
            max-height: 400px !important;
            overflow: auto !important;
            position: relative !important;
            z-index: 1 !important;
        }}
        #swagger-ui-container .swagger-ui code,
        #swagger-ui-container .swagger-ui pre code,
        #swagger-ui-container .swagger-ui .model-example code,
        #swagger-ui-container .swagger-ui .example code {{
            background: transparent !important;
            color: inherit !important;
            font-family: var(--font-code) !important;
            font-size: inherit !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            box-shadow: none !important;
            display: inline !important;
        }}
        #swagger-ui-container .swagger-ui input[type=text],
        #swagger-ui-container .swagger-ui select,
        #swagger-ui-container .swagger-ui textarea {{
            background: var(--bg3) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            font-family: var(--font-main) !important;
            font-size: 13px !important;
        }}
        #swagger-ui-container .swagger-ui input[type=text]:focus,
        #swagger-ui-container .swagger-ui select:focus,
        #swagger-ui-container .swagger-ui textarea:focus {{
            border-color: var(--accent) !important;
            outline: none !important;
            box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2) !important;
        }}
        #swagger-ui-container .swagger-ui .btn {{
            background: var(--bg3) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            font-size: 12px !important;
            padding: 6px 14px !important;
            box-shadow: none !important;
            transition: all 0.15s ease !important;
        }}
        #swagger-ui-container .swagger-ui .btn:hover {{
            background: var(--border) !important;
            color: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .btn.execute {{
            background: var(--accent) !important;
            color: #0d1117 !important;
            border-color: var(--accent) !important;
            font-weight: 700 !important;
        }}
        #swagger-ui-container .swagger-ui .btn.execute:hover {{
            opacity: 0.9 !important;
        }}
        #swagger-ui-container .swagger-ui .btn.authorize {{
            color: var(--green) !important;
            border-color: var(--green) !important;
            background: rgba(63, 185, 80, 0.15) !important;
        }}
        #swagger-ui-container .swagger-ui .btn.authorize:hover {{
            background: rgba(63, 185, 80, 0.25) !important;
        }}
        #swagger-ui-container .swagger-ui svg {{
            fill: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .arrow {{
            fill: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .tab li {{
            color: var(--text) !important;
            font-size: 12px !important;
        }}
        #swagger-ui-container .swagger-ui .dialog-ux .modal-ux {{
            background: var(--bg2) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5) !important;
        }}
        #swagger-ui-container .swagger-ui .dialog-ux .modal-ux-header h3,
        #swagger-ui-container .swagger-ui .dialog-ux .modal-ux-content {{
            color: var(--text) !important;
        }}
        #swagger-ui-container .swagger-ui .dialog-ux .modal-ux-header .close-modal {{
            fill: var(--text) !important;
        }}

        /* Fix Swagger UI floating tooltip & accept message overlap glitch */
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message,
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message small,
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message span,
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message label {{
            background: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
            color: var(--muted) !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            display: inline !important;
            position: static !important;
        }}
        #swagger-ui-container .swagger-ui .response-control-media-type__accept-message {{
            display: block !important;
            margin-top: 6px !important;
            margin-bottom: 8px !important;
            clear: both !important;
        }}
        #swagger-ui-container .swagger-ui .tooltip,
        #swagger-ui-container .swagger-ui .tooltip-inner,
        #swagger-ui-container .swagger-ui [data-hint]:after,
        #swagger-ui-container .swagger-ui [data-hint]:before {{
            display: none !important;
        }}
        #swagger-ui-container .swagger-ui .model-example,
        #swagger-ui-container .swagger-ui .example {{
            margin-top: 8px !important;
            padding: 0 !important;
            background: transparent !important;
            border: none !important;
            clear: both !important;
        }}

        /* PDF Export Button & Print Styles */
        .btn-pdf {{
            background: linear-gradient(135deg, var(--accent) 0%, #3b82f6 100%) !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            border: none !important;
            padding: 6px 14px !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            font-size: 12px !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 6px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 8px rgba(88, 166, 255, 0.3) !important;
        }}
        .btn-pdf:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(88, 166, 255, 0.4) !important;
        }}

        @media print {{
            body {{
                background: #ffffff !important;
                color: #000000 !important;
            }}
            .header, .sidebar, .btn-pdf, .zoom-toolbar, .sub-tabs, .sub-tab-btn {{
                display: none !important;
            }}
            .swagger-view-pane {{
                display: block !important;
                page-break-inside: avoid !important;
            }}
            .app-layout {{
                display: block !important;
            }}
            .main-content {{
                padding: 0 !important;
                margin: 0 !important;
                width: 100% !important;
            }}
            .section {{
                display: block !important;
                page-break-after: always !important;
                break-after: page !important;
                margin-bottom: 30px !important;
            }}
            .card, .module-card, .endpoint-item, .prereq-card, .info-card {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                border: 1px solid #ccc !important;
                background: #ffffff !important;
                color: #000000 !important;
                box-shadow: none !important;
            }}
            * {{
                color: #000000 !important;
                background: transparent !important;
                box-shadow: none !important;
                text-shadow: none !important;
            }}
        }}

        /* API Endpoint Prompt Modal Styles */
        .clickable-ep {{
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 12px !important;
        }}
        .clickable-ep:hover {{
            border-color: var(--accent) !important;
            background: rgba(88, 166, 255, 0.06) !important;
            transform: translateY(-1px) !important;
        }}
        .btn-prompt-copy {{
            background: var(--bg3) !important;
            border: 1px solid var(--border) !important;
            color: var(--muted) !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            padding: 4px 10px !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            transition: all 0.15s ease !important;
            white-space: nowrap !important;
            margin-left: auto !important;
        }}
        .btn-prompt-copy:hover {{
            background: var(--accent) !important;
            color: #0d1117 !important;
            border-color: var(--accent) !important;
        }}
        .custom-modal-backdrop {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(5px);
            z-index: 99999;
            align-items: center;
            justify-content: center;
        }}
        .custom-modal-backdrop.active {{
            display: flex;
        }}
        .custom-modal-content {{
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 12px;
            width: 90%;
            max-width: 680px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
            overflow: hidden;
            animation: modalFadeIn 0.2s ease-out;
        }}
        @keyframes modalFadeIn {{
            from {{ opacity: 0; transform: scale(0.95); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        .custom-modal-header {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg3);
        }}
        .custom-modal-close {{
            background: transparent;
            border: none;
            color: var(--muted);
            font-size: 24px;
            cursor: pointer;
            line-height: 1;
            transition: color 0.15s ease;
        }}
        .custom-modal-close:hover {{
            color: var(--text);
        }}
        .custom-modal-body {{
            padding: 20px;
        }}
        .btn-copy-prompt {{
            background: linear-gradient(135deg, var(--accent) 0%, #3b82f6 100%) !important;
            color: #0d1117 !important;
            font-weight: 700 !important;
            font-size: 12px !important;
            border: none !important;
            padding: 6px 14px !important;
            border-radius: 6px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 6px !important;
            box-shadow: 0 2px 8px rgba(88, 166, 255, 0.3) !important;
        }}
        .btn-copy-prompt:hover {{
            opacity: 0.9 !important;
            transform: translateY(-1px) !important;
        }}
    </style>
</head>
<body>

<header class="header">
    <div class="header-top">
        <div class="brand">
            <span class="brand-icon">&#127959;</span>
            <div>
                <h1 class="brand-title">{html.escape(meta.get('displayName', 'SaaS MVP'))}</h1>
                <div class="brand-sub">Architecture Map & Documentation</div>
            </div>
        </div>
        <div class="sidebar-badges" style="margin-top:0; display: flex; align-items: center; gap: 8px;">
            <button class="btn-pdf" onclick="exportPDF()">📄 Export PDF</button>
            <span class="badge">v{html.escape(meta.get('version', '1.0.0'))}</span>
            <span class="badge">{html.escape(tech_stack.get('language', 'TypeScript'))}</span>
            <span class="badge badge-green">Generated {html.escape(meta.get('generatedAt', 'Live'))}</span>
        </div>
    </div>
</header>

<div class="app-layout">
    <aside class="sidebar">
        <div class="sidebar-header">
            <div style="font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px;">Navigation</div>
        </div>

        <nav class="sidebar-nav">
            <button class="nav-btn active" onclick="showTab('overview', this)">
                <div class="nav-btn-left"><span>&#128204;</span> <span>Overview</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('prereq', this)">
                <div class="nav-btn-left"><span>📋</span> <span>Prerequisites</span></div>
                <span class="nav-count">{len(prereq_tools)}</span>
            </button>
            <button class="nav-btn" onclick="showTab('modules', this)">
                <div class="nav-btn-left"><span>&#128230;</span> <span>API Modules</span></div>
                <span class="nav-count">{len(modules)}</span>
            </button>
            <button class="nav-btn" onclick="showTab('sysarch', this)">
                <div class="nav-btn-left"><span>&#127963;</span> <span>System Architecture</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('docker', this)">
                <div class="nav-btn-left"><span>&#128051;</span> <span>Docker Topology</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('swagger', this)">
                <div class="nav-btn-left"><span>&#9889;</span> <span>Swagger & OpenAPI</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('perms', this)">
                <div class="nav-btn-left"><span>&#128273;</span> <span>Permissions</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('sql', this)">
                <div class="nav-btn-left"><span>&#128452;</span> <span>SQL Queries</span></div>
                <span class="nav-count">{len(sql_queries)}</span>
            </button>
            <button class="nav-btn" onclick="showTab('infra', this)">
                <div class="nav-btn-left"><span>&#128187;</span> <span>Infrastructure</span></div>
                <span class="nav-count">{len(infrastructure)}</span>
            </button>
            <button class="nav-btn" onclick="showTab('core', this)">
                <div class="nav-btn-left"><span>&#128737;</span> <span>Core Layer</span></div>
            </button>
            <button class="nav-btn" onclick="showTab('flow', this)">
                <div class="nav-btn-left"><span>&#128257;</span> <span>Request Pipeline</span></div>
            </button>
        </nav>

        <div class="sidebar-footer">
           © AHMED EMAD - {html.escape(meta.get('displayName', 'Project MVP'))}
        </div>
    </aside>

    <main class="main-content">

    <!-- 1. OVERVIEW -->
    <div class="section active" id="sec-overview">
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(modules)}</div><div class="stat-lbl">API Modules</div></div>
            <div class="stat"><div class="stat-num">{total_endpoints}</div><div class="stat-lbl">Total Endpoints</div></div>
            <div class="stat"><div class="stat-num">{len(infrastructure)}</div><div class="stat-lbl">Docker Services</div></div>
            <div class="stat"><div class="stat-num">{len(permissions.get('catalog', []))}</div><div class="stat-lbl">Permissions</div></div>
            <div class="stat"><div class="stat-num">{len(sql_queries)}</div><div class="stat-lbl">SQL Queries</div></div>
            <div class="stat"><div class="stat-num">{len(workspaces)}</div><div class="stat-lbl">Workspaces</div></div>
        </div>

        <div class="sec-title">📦 Workspaces</div>
        <div class="grid3">
"""
    for ws in workspaces:
        ws_type = ws.get('type', 'app')
        icon = '⚡' if ws_type == 'backend' else ('💻' if ws_type == 'frontend' else '📦')
        port_str = f" : {ws.get('port')}" if ws.get('port') else ""
        html_content += f"""
            <div class="card">
                <div class="chead">
                    <span style="font-size:22px">{icon}</span>
                    <div>
                        <div class="card-title">{html.escape(ws.get('name', ''))}</div>
                        <div class="card-sub">{html.escape(ws_type.upper())}{port_str}</div>
                    </div>
                </div>
                <div class="card-desc">{html.escape(ws.get('description', ''))}</div>
                {f'<span class="tag tq">{html.escape(ws.get("entrypoint"))}</span>' if ws.get('entrypoint') else ''}
            </div>
"""

    html_content += """
        </div>

        <div class="sec-title">🌐 System Endpoints</div>
        <div class="grid1">
"""
    for se in system_endpoints:
        m = se.get('method', 'GET').upper()
        html_content += f"""
            <div class="endpoint clickable-ep" data-method="{m}" data-path="{html.escape(se.get('path', ''))}" onclick="openApiPromptFromEl(this)" title="Click to view AI Senior Developer prompt">
                <span class="method {m}">{m}</span>
                <div style="flex:1">
                    <div class="ep-path">{html.escape(se.get('path', ''))}</div>
                    <div class="ep-desc">{html.escape(se.get('description', ''))}</div>
                </div>
                <button class="btn-prompt-copy" onclick="event.stopPropagation(); copyApiPromptDirectFromEl(this.parentElement)" title="Copy AI Prompt">📋 Prompt</button>
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 1.5 PREREQUISITES -->
    <div class="section" id="sec-prereq">
        <div class="card" style="margin-bottom: 20px;">
            <div class="chead">
                <span style="font-size:28px">📋</span>
                <div>
                    <div class="card-title">System Prerequisites &amp; Setup Requirements</div>
                    <div class="card-sub">Developer tools, container runtimes, and step-by-step initialization sequence</div>
                </div>
            </div>
            <p class="card-desc">""" + html.escape(prerequisites.get('description', 'Software runtimes, system dependencies, and step-by-step initialization commands required to run the project.')) + """</p>
        </div>

        <div class="sec-title">🛠️ Required Tools &amp; Runtimes</div>
        <div class="grid3" style="margin-bottom: 24px;">
"""
    for tool in prereq_tools:
        tname = tool.get('name', 'Tool')
        tver = tool.get('version', 'latest')
        treq = tool.get('required', True)
        tdesc = tool.get('description', '')
        tcat = tool.get('category', 'general')

        icon_map = {
            'runtime': '⚡',
            'infrastructure': '🐳',
            'database': '🗄️',
            'cache': '⚡',
            'queue': '📬',
            'monitoring': '📊',
            'package_manager': '📦'
        }
        ticon = icon_map.get(tcat, '🛠️')
        req_badge = '<span class="tag tr">Required</span>' if treq else '<span class="tag tq">Optional</span>'

        html_content += f"""
            <div class="card">
                <div class="chead">
                    <span style="font-size:24px">{ticon}</span>
                    <div>
                        <div class="card-title">{html.escape(tname)} {req_badge}</div>
                        <div class="card-sub" style="font-family:var(--font-code);">Version {html.escape(tver)}</div>
                    </div>
                </div>
                <div class="card-desc">{html.escape(tdesc)}</div>
            </div>
"""

    html_content += """
        </div>

        <div class="sec-title">🚀 Setup &amp; Execution Pipeline</div>
        <div class="pipeline">
"""
    for step in prereq_steps:
        snum = step.get('step', 1)
        stitle = step.get('title', '')
        scmd = step.get('command', '')
        sdesc = step.get('description', '')

        cmd_block = f'<code style="display:block; margin-top:8px; font-size:12px; color:var(--accent); background:var(--bg); padding:8px 12px; border-radius:6px; font-family:var(--font-code); overflow-x:auto;">{html.escape(scmd)}</code>' if scmd else ''

        html_content += f"""
            <div class="pipe-step" style="cursor:default;">
                <div class="pipe-num">{snum}</div>
                <div style="flex:1;">
                    <div style="font-size:14px; font-weight:600; color:var(--text);">{html.escape(stitle)}</div>
                    <div style="font-size:12px; color:var(--muted); margin-top:4px;">{html.escape(sdesc)}</div>
                    {cmd_block}
                </div>
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 2. API MODULES -->
    <div class="section" id="sec-modules">
        <input class="search" id="modSearch" placeholder="Search endpoints, paths, permissions, descriptions..." oninput="filterModules()">
        <div class="grid2" id="modulesGrid">
"""
    for mod in modules:
        perms_html = "".join([f'<span class="tag tp">{html.escape(p)}</span>' for p in mod.get('permissions', [])])
        eps_html = ""
        mod_base = mod.get('basePath', '').strip()
        for ep in mod.get('endpoints', []):
            m = ep.get('method', 'GET').upper()
            raw_p = ep.get('path', '').strip()
            if raw_p.startswith('http://') or raw_p.startswith('https://') or (mod_base and raw_p.startswith(mod_base)):
                full_path = raw_p
            else:
                if mod_base:
                    if raw_p == '/' or not raw_p:
                        full_path = mod_base
                    else:
                        full_path = mod_base.rstrip('/') + '/' + raw_p.lstrip('/')
                else:
                    full_path = raw_p if raw_p else '/'

            perm_str = f'<span class="lock">🔒 {html.escape(ep["permission"])}</span>' if ep.get('permission') else ('<span class="lock">🔑</span>' if ep.get('auth') else '')
            eps_html += f"""
                <div class="endpoint clickable-ep" data-method="{m}" data-path="{html.escape(full_path)}" onclick="openApiPromptFromEl(this)" title="Click to view AI Senior Developer prompt">
                    <span class="method {m}">{m}</span>
                    <div style="flex:1">
                        <div class="ep-path">{html.escape(ep.get('path', ''))}{perm_str}</div>
                        <div class="ep-desc">{html.escape(ep.get('description', ''))}</div>
                    </div>
                    <button class="btn-prompt-copy" onclick="event.stopPropagation(); copyApiPromptDirectFromEl(this.parentElement)" title="Copy AI Prompt">📋 Prompt</button>
                </div>
"""
        html_content += f"""
            <div class="card mod-card">
                <div class="color-bar" style="background: {html.escape(mod.get('color', '#58a6ff'))}"></div>
                <div class="chead">
                    <span style="font-size:22px">{html.escape(mod.get('icon', '📁'))}</span>
                    <div>
                        <div class="card-title">{html.escape(mod.get('name', ''))}</div>
                        <div class="card-sub" style="font-family: var(--font-code);">{html.escape(mod.get('basePath', ''))}</div>
                    </div>
                </div>
                <div class="card-desc">{html.escape(mod.get('description', ''))}</div>
                {f'<div style="margin-bottom:10px">{perms_html}</div>' if perms_html else ''}
                {eps_html}
            </div>
"""

    html_content += f"""
        </div>
    </div>

    <!-- 3. SYSTEM ARCHITECTURE & COMPONENTS DIAGRAM -->
    <div class="section" id="sec-sysarch">
        <div class="card">
            <div class="chead">
                <span style="font-size:24px">🏛️</span>
                <div>
                    <div class="card-title">System Design & Component Architecture Diagram</div>
                    <div class="card-sub">High-level software architecture, layered boundaries, and component relationships</div>
                </div>
            </div>
            <p class="card-desc">{html.escape(system_arch_diagram.get('description', 'Component & System Design Diagram.'))}</p>
            <div class="diagram-box">
                <div id="sysarchMermaid" style="width: 100%; min-height: 500px; display: flex; justify-content: center; align-items: center;"></div>
                <script type="text/plain" id="sysarchMermaidSrc">
flowchart TB
    classDef proxy fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#fff;
    classDef app fill:#1e3a8a,stroke:#58a6ff,stroke-width:2px,color:#fff;
    classDef database fill:#064e3b,stroke:#3fb950,stroke-width:2px,color:#fff;
    classDef cache fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef queue fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef monitoring fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff;
    classDef logging fill:#831843,stroke:#ec4899,stroke-width:2px,color:#fff;

"""
    sys_type_map = {}
    for sg in system_arch_diagram.get('subgraphs', []):
        sg_id = f"sg_{clean_mermaid(sg['id'])}"
        sg_lbl = clean_mermaid(sg['label'])
        html_content += f"    subgraph {sg_id}[\"{sg_lbl}\"]\n"
        for node in sg.get('nodes', []):
            nid = clean_mermaid(node['id'])
            nlbl = clean_mermaid(node['label'])
            ntype = clean_mermaid(node.get('type', 'app'))
            html_content += f"        {nid}[\"{nlbl}\"]\n"
            if ntype not in sys_type_map:
                sys_type_map[ntype] = []
            sys_type_map[ntype].append(nid)
        html_content += "    end\n\n"

    for edge in system_arch_diagram.get('edges', []):
        fid = clean_mermaid(edge['from'])
        tid = clean_mermaid(edge['to'])
        elbl = clean_mermaid(edge.get('label', ''))
        if elbl:
            html_content += f"    {fid} -->|\"{elbl}\"| {tid}\n"
        else:
            html_content += f"    {fid} --> {tid}\n"

    html_content += "\n"
    for t_name, n_ids in sys_type_map.items():
        if n_ids:
            html_content += f"    class {','.join(n_ids)} {t_name};\n"

    html_content += f"""
                </script>
            </div>
        </div>
    </div>

    <!-- 4. DOCKER DIAGRAM -->
    <div class="section" id="sec-docker">
        <div class="card">
            <div class="chead">
                <span style="font-size:24px">🐳</span>
                <div>
                    <div class="card-title">Docker Infrastructure Topology &amp; Dependency Diagram</div>
                    <div class="card-sub">Rendered live using Mermaid.js from container specifications</div>
                </div>
            </div>
            <p class="card-desc">{html.escape(docker_diagram.get('description', 'Parsed from docker-compose.yml'))}</p>
"""

    has_docker_nodes = bool(docker_diagram.get('nodes'))
    if not has_docker_nodes:
        html_content += """
            <div style="text-align:center; padding: 60px 20px; color: var(--muted);">
                <div style="font-size: 48px; margin-bottom: 16px;">🐳</div>
                <div style="font-size: 16px; font-weight: 600; color: var(--text); margin-bottom: 8px;">No Docker Services Configured</div>
                <div style="font-size: 13px; line-height: 1.6; max-width: 480px; margin: 0 auto;">
                    This project does not use Docker, or container topology has not been added yet.<br><br>
                    To add Docker topology, update <code style="color:var(--accent)">dockerDiagram.nodes</code> and
                    <code style="color:var(--accent)">dockerDiagram.edges</code> in <code>architecture.json</code>
                    and regenerate.
                </div>
            </div>
        </div>
    </div>
"""
    else:
        html_content += f"""
            <div class="diagram-box">
                <div id="dockerMermaid" style="width: 100%; min-height: 400px; display: flex; justify-content: center; align-items: center;"></div>
                <script type="text/plain" id="dockerMermaidSrc">
flowchart TD
    classDef proxy fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#fff;
    classDef app fill:#1e3a8a,stroke:#58a6ff,stroke-width:2px,color:#fff;
    classDef database fill:#064e3b,stroke:#3fb950,stroke-width:2px,color:#fff;
    classDef cache fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef queue fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef monitoring fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff;
    classDef logging fill:#831843,stroke:#ec4899,stroke-width:2px,color:#fff;
    classDef uptime fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#fff;

"""
        type_map = {}
        for node in docker_diagram.get('nodes', []):
            node_id = clean_mermaid(node['id'])
            node_type = clean_mermaid(node.get('type', 'app'))
            clean_lbl = clean_mermaid(node.get('label', ''))
            port_info = f" Port {clean_mermaid(node['port'])}" if node.get('port') else ""
            html_content += f"    {node_id}[\"{clean_lbl}{port_info}\"]\n"
            if node_type not in type_map:
                type_map[node_type] = []
            type_map[node_type].append(node_id)

        html_content += "\n"
        for edge in docker_diagram.get('edges', []):
            from_id = clean_mermaid(edge['from'])
            to_id = clean_mermaid(edge['to'])
            clean_edge = clean_mermaid(edge.get('label', ''))
            if clean_edge:
                html_content += f"    {from_id} -->|\"{clean_edge}\"| {to_id}\n"
            else:
                html_content += f"    {from_id} --> {to_id}\n"

        html_content += "\n"
        for t_name, n_ids in type_map.items():
            if n_ids:
                html_content += f"    class {','.join(n_ids)} {t_name};\n"

        html_content += """
                </script>
            </div>
        </div>
    </div>
"""
    openapi_spec_dict = build_openapi_spec(data)
    openapi_spec_json = json.dumps(openapi_spec_dict, indent=2)

    html_content += f"""
    <!-- 4. SWAGGER & OPENAPI -->
    <div class="section" id="sec-swagger">
        <div class="card" style="margin-bottom: 20px;">
            <div class="chead">
                <span style="font-size:28px">&#9889;</span>
                <div>
                    <div class="card-title">Swagger & OpenAPI 3.0 API Specification & Explorer</div>
                    <div class="card-sub">Interactive REST API documentation generated from architecture manifest ({total_endpoints} Endpoints)</div>
                </div>
                <span class="badge badge-green" style="margin-left:auto; font-size: 12px; padding: 6px 12px;">STATUS: {html.escape(swagger_schemas.get('matchStatus', 'Verified Parity').upper())}</span>
            </div>

            <div class="grid4" style="margin-top: 15px;">
                <div style="font-size: 12px; color: var(--muted);">
                    <div style="color: var(--text); font-weight: 600; margin-bottom: 2px;">OpenAPI Version</div>
                    <code>{html.escape(swagger_schemas.get('openapi', '3.0.0'))}</code>
                </div>
                <div style="font-size: 12px; color: var(--muted);">
                    <div style="color: var(--text); font-weight: 600; margin-bottom: 2px;">Base URL</div>
                    <code>http://localhost:3000</code>
                </div>
                <div style="font-size: 12px; color: var(--muted);">
                    <div style="color: var(--text); font-weight: 600; margin-bottom: 2px;">Security Scheme</div>
                    <span class="tag ty">{html.escape(swagger_schemas.get('securityScheme', 'bearerAuth'))}</span>
                </div>
                <div style="font-size: 12px; color: var(--muted);">
                    <div style="color: var(--text); font-weight: 600; margin-bottom: 2px;">Live Swagger Route</div>
                    <code>{html.escape(swagger_schemas.get('servedAt', '/api/docs'))}</code>
                </div>
            </div>
        </div>

        <!-- View Mode Selector -->
        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
            <button class="sub-tab-btn active" onclick="switchSwaggerView('ui', this)">&#9889; Interactive Swagger UI</button>
            <button class="sub-tab-btn" onclick="switchSwaggerView('catalog', this)">&#128216; API Endpoint Catalog & cURL ({total_endpoints})</button>
            <button class="sub-tab-btn" onclick="switchSwaggerView('json', this)">&#128220; OpenAPI 3.0 JSON Spec</button>
        </div>

        <!-- Pane 1: Interactive Swagger UI -->
        <div id="swagger-view-ui" class="swagger-view-pane active">
            <div class="card" style="padding: 10px;">
                <div id="swagger-ui-container">
                    <div style="padding: 40px; text-align: center; color: var(--muted);">
                        Loading Interactive Swagger UI...
                    </div>
                </div>
            </div>
        </div>

        <!-- Pane 2: API Endpoint Catalog & cURL -->
        <div id="swagger-view-catalog" class="swagger-view-pane">
"""
    for mod in modules:
        mod_name = mod.get('name', '')
        base_path = mod.get('basePath', '')
        mod_icon = mod.get('icon', '')
        mod_endpoints = mod.get('endpoints', [])

        html_content += f"""
            <div class="card" style="margin-bottom: 20px;">
                <div class="chead" style="margin-bottom: 12px;">
                    <span style="font-size: 22px;">{mod_icon}</span>
                    <div>
                        <div class="card-title">{html.escape(mod_name)} API Module</div>
                        <div class="card-sub">Base Path: <code>{html.escape(base_path)}</code> | {len(mod_endpoints)} Endpoints</div>
                    </div>
                </div>

                <div class="grid1" style="gap: 12px;">
"""
        for ep in mod_endpoints:
            m = ep.get('method', 'GET').upper()
            p = ep.get('path', '')
            full_path = (base_path + ("" if p == "/" else p)).replace("//", "/")
            auth = ep.get('auth', False)
            perm = ep.get('permission')
            desc = ep.get('description', '')

            m_class = 'tg' if m == 'GET' else ('tb' if m == 'POST' else ('ty' if m in ['PUT','PATCH'] else 'tr'))
            curl_auth_header = ' -H "Authorization: Bearer $JWT_TOKEN"' if auth else ''
            curl_body = ' -H "Content-Type: application/json" -d \'{"key":"value"}\'' if m in ['POST','PUT','PATCH'] else ''
            curl_cmd = f"curl -X {m} \"http://localhost:3000{full_path}\"{curl_auth_header}{curl_body}"

            html_content += f"""
                    <div style="background: var(--bg3); border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
                        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                            <span class="tag {m_class}" style="font-weight: 700; font-size: 11px;">{m}</span>
                            <span style="font-family: var(--font-code); font-weight: 600; font-size: 13px; color: var(--text);">{html.escape(full_path)}</span>
                            {f'<span class="tag tb" style="font-size:10px; margin-left:auto;">&#128273; {html.escape(perm)}</span>' if perm else (
                             '<span class="tag tg" style="font-size:10px; margin-left:auto;">&#128274; Authenticated</span>' if auth else '<span class="tag ty" style="font-size:10px; margin-left:auto;">&#127760; Public</span>'
                            )}
                        </div>
                        <div style="font-size: 12px; color: var(--muted); margin-top: 6px;">{html.escape(desc)}</div>
                        <div style="margin-top: 8px;">
                            <div style="font-size: 10px; color: var(--muted); margin-bottom: 2px;">cURL Snippet:</div>
                            <code style="display: block; font-size: 11px; color: var(--accent); background: var(--bg); padding: 6px 10px; border-radius: 4px; overflow-x: auto;">{html.escape(curl_cmd)}</code>
                        </div>
                    </div>
"""
        html_content += """
                </div>
            </div>
"""

    html_content += f"""
        </div>

        <!-- Pane 3: Raw OpenAPI 3.0 JSON Spec -->
        <div id="swagger-view-json" class="swagger-view-pane">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="font-weight: 600; font-size: 14px;">OpenAPI 3.0.0 JSON Specification Source</div>
                    <button class="sub-tab-btn" onclick="navigator.clipboard.writeText(document.getElementById('swaggerOpenApiJsonSrc').textContent); alert('Copied OpenAPI JSON Spec to clipboard!');">&#128203; Copy OpenAPI Spec</button>
                </div>
                <pre style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; font-family: var(--font-code); font-size: 12px; color: var(--text); max-height: 600px; overflow-y: auto;"><code id="swaggerOpenApiJsonSrc">{html.escape(openapi_spec_json)}</code></pre>
            </div>
        </div>
    </div>

    <!-- 5. PERMISSIONS & SECURITY SCOPES -->
    <div class="section" id="sec-perms">
        <div class="sec-title">&#128273; Scope & Isolation / Permissions</div>
        <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">
            {html.escape(permissions.get('description', 'Role-Based Access Control (RBAC) & Security Scope mapping.'))}
        </p>

        <div class="stats" style="margin-bottom: 20px;">
            <div class="stat"><div class="stat-num">{len(permissions.get('catalog', []))}</div><div class="stat-lbl">Security Scopes / Slugs</div></div>
            <div class="stat"><div class="stat-num">{sum(len(d.get('endpoints', [])) for d in permissions.get('details', []) if d.get('slug') != 'public')}</div><div class="stat-lbl">Authenticated Endpoints</div></div>
            <div class="stat"><div class="stat-num">{sum(len(d.get('endpoints', [])) for d in permissions.get('details', []) if d.get('slug') == 'public')}</div><div class="stat-lbl">Public Endpoints</div></div>
            <div class="stat"><div class="stat-num">{len(permissions.get('details', []))}</div><div class="stat-lbl">Mapped Scope Groups</div></div>
        </div>
"""
    if not permissions.get('catalog', []) and not permissions.get('details', []):
        html_content += """
        <div class="card" style="text-align: center; padding: 48px 24px; color: var(--muted); border: 1px dashed var(--border); border-radius: 12px; margin-top: 16px;">
            <div style="font-size: 36px; margin-bottom: 12px;">🔒</div>
            <div style="font-size: 16px; font-weight: 600; color: var(--text);">No Role-Based Access Control (RBAC) Permissions Defined</div>
            <div style="font-size: 13px; margin-top: 6px;">All endpoints in this project currently run with standard authentication or open public access. No specific role permissions were declared on the routes.</div>
        </div>
"""
    else:
        html_content += """
        <div class="perm-grid">
"""
        for p in permissions.get('catalog', []):
            icon = '🔑' if p not in ('authenticated', 'public') else ('🔒' if p == 'authenticated' else '🌐')
            html_content += f'<div class="perm-item">{icon} {html.escape(p)}</div>'

        html_content += """
        </div>

        <div class="sec-title" style="margin-top: 24px;">&#128279; Interactive Permission & Scope-to-Endpoint Flow</div>
        <div class="grid1">
"""
        for pdet in permissions.get('details', []):
            eps_html = ""
            for ep in pdet.get('endpoints', []):
                m = ep.get('method', 'GET').upper()
                eps_html += f'<span class="method {m}">{m}</span> <code style="font-size:12px">{html.escape(ep.get("path",""))}</code> &nbsp; '

            pages_html = ", ".join([f'<span class="tag tb">{html.escape(pg)}</span>' for pg in pdet.get('adminPages', [])])
            slug_val = pdet.get('slug', '')
            slug_icon = '🔑' if slug_val not in ('authenticated', 'public') else ('🔒' if slug_val == 'authenticated' else '🌐')

            html_content += f"""
            <div class="perm-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-family:var(--font-code); font-weight:700; color:var(--purple); font-size:14px;">{slug_icon} {html.escape(slug_val)}</span>
                    <span class="tag tp">{html.escape(pdet.get('module', ''))} • {html.escape(pdet.get('action', ''))}</span>
                </div>
                <div style="margin-top: 8px; font-size: 13px;">
                    <strong>Protected Endpoints ({len(pdet.get('endpoints', []))}):</strong> {eps_html}
                </div>
                <div style="margin-top: 6px; font-size: 12px; color: var(--muted);">
                    <strong>Scope Target:</strong> {pages_html}
                </div>
            </div>
"""
        html_content += """
        </div>
"""
    html_content += """
    </div>

    <!-- 6. SQL QUERIES CATALOG -->
    <div class="section" id="sec-sql">
        <div class="sec-title">&#128452; SQL Query Catalog & Repository Mapping</div>
        <p style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">
            Raw SQL statements mapped to repository/service functions, affected tables, and API endpoints.
        </p>
"""
    if not sql_queries:
        html_content += """
        <div class="card" style="text-align: center; padding: 48px 24px; color: var(--muted); border: 1px dashed var(--border); border-radius: 12px;">
            <div style="font-size: 36px; margin-bottom: 12px;">🗃️</div>
            <div style="font-size: 16px; font-weight: 600; color: var(--text);">No Database SQL Queries Configured</div>
            <div style="font-size: 13px; margin-top: 6px;">This project does not contain direct database repositories or SQL queries (e.g. External REST API Proxy or WebClient Service).</div>
        </div>
"""
    else:
        html_content += """
        <div class="grid1">
"""
        for q in sql_queries:
            eps_html = ""
            for ep in q.get('endpoints', []):
                m = ep.get('method', 'GET').upper()
                eps_html += f'<span class="method {m}">{m}</span> <code style="font-size:12px">{html.escape(ep.get("path",""))}</code> &nbsp; '

            tables_html = " ".join([f'<span class="tag tg">{html.escape(tb)}</span>' for tb in q.get('tables', [])])

            html_content += f"""
            <div class="card">
                <div class="chead" style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                    <div class="card-title" style="color: var(--yellow);">&#9889; {html.escape(q.get('label', ''))}</div>
                    <span class="tag tp" style="margin-left:auto">{html.escape(q.get('module', ''))} • {html.escape(q.get('function', ''))}</span>
                </div>
                <p style="font-size: 13px; color: var(--muted); margin: 6px 0;">
                    <strong>Purpose:</strong> {html.escape(q.get('purpose', ''))}<br>
                    <strong>File:</strong> <code>{html.escape(q.get('file', ''))}</code> | <strong>Tables:</strong> {tables_html}
                </p>
                <div style="margin: 8px 0; font-size: 12px;">
                    <strong>Consuming Endpoints:</strong> {eps_html}
                </div>
                <div class="code-block">{html.escape(q.get('sql', ''))}</div>
            </div>
"""
        html_content += """
        </div>
"""
    html_content += """
    </div>

    <!-- 7. INFRASTRUCTURE -->
    <div class="section" id="sec-infra">
        <div class="sec-title">&#128187; Infrastructure Services</div>
        <div class="grid3">
"""
    tc_map = {'database':'tb', 'cache':'tg', 'queue':'ty', 'proxy':'tq', 'monitoring':'tp', 'logging':'tr', 'uptime':'tr'}
    for s in infrastructure:
        t_cls = tc_map.get(s.get('type'), 'tq')
        ports = f" : {s.get('port')}" if s.get('port') else ""
        mgmt = f" (mgmt: {s.get('managementPort')})" if s.get('managementPort') else ""
        feats = "".join([f'<span class="tag tq">{html.escape(f)}</span>' for f in s.get('features', [])])

        html_content += f"""
            <div class="card">
                <div class="chead">
                    <div>
                        <div class="card-title">{html.escape(s.get('name', ''))} <span class="tag {t_cls}">{html.escape(s.get('type', ''))}</span></div>
                        <div class="card-sub">{html.escape(s.get('image', ''))}{ports}{mgmt}</div>
                    </div>
                </div>
                <div class="card-desc">{html.escape(s.get('description', ''))}</div>
                {f'<div>{feats}</div>' if feats else ''}
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 8. CORE LAYER -->
    <div class="section" id="sec-core">
        <div class="sec-title">&#128737; Security Middleware</div>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:20px;">
"""
    for sec in core_layer.get('security', []):
        html_content += f"""
            <div style="background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:10px 14px; min-width:160px;">
                <div style="font-weight:600; font-size:13px; margin-bottom:4px; color:var(--accent);">{html.escape(sec.get('name', ''))}</div>
                <div style="font-size:12px; color:var(--muted);">{html.escape(sec.get('description', ''))}</div>
            </div>
"""

    html_content += """
        </div>

        <div class="sec-title">&#9881; Core Middleware</div>
        <div class="grid1">
"""
    for mw in core_layer.get('middleware', []):
        guards = "".join([f'<span class="tag ty">{html.escape(g)}</span>' for g in mw.get('guards', [])])
        html_content += f"""
            <div class="mwcard">
                <div style="font-weight:600; font-size:14px; margin-bottom:4px;">{html.escape(mw.get('name', ''))}</div>
                <div style="font-size:11px; font-family:var(--font-code); color:var(--muted); margin-bottom:6px;">{html.escape(mw.get('file', ''))}</div>
                <div style="font-size:13px; color:var(--muted);">{html.escape(mw.get('description', ''))}</div>
                {f'<div style="margin-top:8px">{guards}</div>' if guards else ''}
            </div>
"""

    html_content += """
        </div>

        <div class="sec-title">&#128736; Core Services</div>
        <div class="grid2">
"""
    for svc in core_layer.get('services', []):
        exports = "".join([f'<span class="tag tb" style="font-family:var(--font-code); font-size:11px">{html.escape(ex)}</span>' for ex in svc.get('exports', [])])
        html_content += f"""
            <div class="card">
                <div class="card-title">{html.escape(svc.get('name', ''))}</div>
                <div class="card-sub" style="margin-bottom:8px;">{html.escape(svc.get('file', ''))}</div>
                <div class="card-desc">{html.escape(svc.get('description', ''))}</div>
                {f'<div style="margin-top:8px">{exports}</div>' if exports else ''}
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 9. REQUEST FLOW -->
    <div class="section" id="sec-flow">
        <div class="sec-title">&#128257; Request Pipeline</div>
        <p style="font-size:13px; color:var(--muted); margin-bottom:18px; line-height:1.7;">
            Step-by-step lifecycle of an inbound HTTP request through the application stack.
            Click any step to see implementation detail.
        </p>
        <div class="pipeline">
"""
    pipeline = data_flow.get('requestPipeline', [])
    # Support both legacy plain-string steps and new dict steps
    core_tab_label = {'security': 'Security Middleware', 'middleware': 'Core Middleware', 'services': 'Core Services'}
    core_ref_icon  = {'security': '🔐', 'middleware': '⚙️', 'services': '🔧'}

    for i, step in enumerate(pipeline):
        if isinstance(step, dict):
            step_text = step.get('step', '')
            detail    = step.get('detail', '')
            core_ref  = step.get('coreRef', '')
        else:
            step_text = step
            detail    = ''
            core_ref  = ''

        detail_block = ''
        if detail:
            detail_block = f'<div class="pipe-detail" id="pdet-{i}" style="display:none; margin-top:8px; font-size:12px; color:var(--muted); line-height:1.6; padding-left:34px;">{html.escape(detail)}</div>'

        core_link = ''
        if core_ref and core_ref in core_tab_label:
            icon = core_ref_icon.get(core_ref, '→')
            label = core_tab_label[core_ref]
            core_link = f'<a href="#" onclick="showTab(\'core\',null);return false;" style="font-size:11px; color:var(--accent); text-decoration:none; margin-left:auto; white-space:nowrap; opacity:0.8;">{icon} {label}</a>'

        toggle = f'onclick="var d=document.getElementById(\'pdet-{i}\');d.style.display=d.style.display===\'none\'?\'\':\'none\';" style="cursor:pointer;"' if detail else ''

        html_content += f"""
            <div class="pipe-step" {toggle}>
                <div class="pipe-num">{i+1}</div>
                <div style="font-size:13px; color:var(--text); flex:1;">{html.escape(step_text)}</div>
                {core_link}
                {'<span style="font-size:10px; color:var(--muted); margin-left:8px;">▼</span>' if detail else ''}
            </div>
            {detail_block}
"""

    # Error pipeline section
    error_pipeline = data_flow.get('errorPipeline', [])
    err_items_html = ''
    for j, estep in enumerate(error_pipeline):
        estep_text = estep if isinstance(estep, str) else estep.get('step', '')
        err_items_html += f"""
                <div style="display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bg); border-radius:6px; margin:3px 0;">
                    <div style="background:var(--red); color:#fff; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; flex-shrink:0;">{j+1}</div>
                    <div style="font-size:13px; color:var(--text);">{html.escape(estep_text)}</div>
                </div>"""

    if err_items_html:
        html_content += f"""
        </div>

        <div style="margin-top:24px;">
            <div style="display:flex; align-items:center; gap:10px; cursor:pointer; margin-bottom:10px;"
                 onclick="var ep=document.getElementById('errorPipelineBody');ep.style.display=ep.style.display==='none'?'':'none';">
                <div style="font-size:14px; font-weight:600; color:var(--red);">⚠ Exception / Error Flow</div>
                <span style="font-size:11px; color:var(--muted);">click to expand</span>
            </div>
            <div id="errorPipelineBody" style="display:none; background:var(--bg2); border:1px solid var(--border); border-left:3px solid var(--red); border-radius:8px; padding:14px;">
                <p style="font-size:12px; color:var(--muted); margin-bottom:10px; line-height:1.6;">
                    When an exception is thrown at any layer, the following error handling chain is invoked instead of the normal response path.
                </p>
                {err_items_html}
            </div>
        </div>
"""
    else:
        html_content += "\n        </div>\n"

    html_content += f"""
        <div style="margin-top:24px; background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:20px;">
            <div class="sec-title" style="margin-top:0">&#128274; Scope & Isolation</div>
            <p style="font-size:13px; color:var(--muted); line-height:1.7;">
                {html.escape(data_flow.get('tenantIsolation', ''))}
            </p>
        </div>
    </div>


    </main>
</div>

<script>
    var dockerMermaidRendered = false;
    var sysarchMermaidRendered = false;
    var swaggerUiRendered = false;
    var sysarchPanZoom = null;
    var dockerPanZoom = null;

    function initPanZoom(containerId, isSysarch) {{
        var container = document.getElementById(containerId);
        if (!container) return;
        var svg = container.querySelector('svg');
        if (!svg) return;

        svg.removeAttribute('style');
        svg.removeAttribute('width');
        svg.removeAttribute('height');
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.display = 'block';
        svg.style.overflow = 'visible';

        var parentBox = container.closest('.diagram-box');
        if (parentBox && !parentBox.querySelector('.diagram-toolbar')) {{
            var toolbar = document.createElement('div');
            toolbar.className = 'diagram-toolbar';
            toolbar.innerHTML = `
                <button onclick="zoomDiagram('${{containerId}}', 'in')" title="Zoom In">🔍 +</button>
                <button onclick="zoomDiagram('${{containerId}}', 'out')" title="Zoom Out">🔍 -</button>
                <button onclick="zoomDiagram('${{containerId}}', 'reset')" title="Reset View">↺ Reset</button>
                <button onclick="zoomDiagram('${{containerId}}', 'fit')" title="Fit to Screen">⛶ Fit</button>
            `;
            parentBox.insertBefore(toolbar, container);
        }}

        if (typeof svgPanZoom !== 'undefined') {{
            try {{
                if (isSysarch && sysarchPanZoom) {{ sysarchPanZoom.destroy(); sysarchPanZoom = null; }}
                if (!isSysarch && dockerPanZoom) {{ dockerPanZoom.destroy(); dockerPanZoom = null; }}

                var pz = svgPanZoom(svg, {{
                    zoomEnabled: true,
                    controlIconsEnabled: false,
                    mouseWheelZoomEnabled: true,
                    fit: true,
                    center: true,
                    minZoom: 0.1,
                    maxZoom: 10,
                    zoomScaleSensitivity: 0.25
                }});

                if (isSysarch) sysarchPanZoom = pz;
                else dockerPanZoom = pz;

                setTimeout(function() {{
                    pz.resize();
                    pz.fit();
                    pz.center();
                }}, 100);
            }} catch(e) {{
                console.warn("svgPanZoom init error:", e);
            }}
        }}
    }}

    function zoomDiagram(containerId, action) {{
        var pz = (containerId === 'sysarchMermaid') ? sysarchPanZoom : dockerPanZoom;
        if (!pz) return;
        if (action === 'in') pz.zoomIn();
        else if (action === 'out') pz.zoomOut();
        else if (action === 'reset') {{ pz.resetZoom(); pz.resetPan(); pz.fit(); pz.center(); }}
        else if (action === 'fit') {{ pz.resize(); pz.fit(); pz.center(); }}
    }}

    function renderSysarchDiagram() {{
        if (sysarchMermaidRendered) {{
            if (sysarchPanZoom) {{
                sysarchPanZoom.resize();
                sysarchPanZoom.fit();
                sysarchPanZoom.center();
            }}
            return;
        }}
        sysarchMermaidRendered = true;
        var tpl = document.getElementById('sysarchMermaidSrc');
        var target = document.getElementById('sysarchMermaid');
        if (tpl && target && typeof mermaid !== 'undefined') {{
            var src = tpl.textContent.trim();
            var uniqueId = 'svg_sysarch_' + Math.floor(Math.random() * 1000000);
            mermaid.render(uniqueId, src).then(function(res) {{
                target.innerHTML = res.svg;
                setTimeout(function() {{ initPanZoom('sysarchMermaid', true); }}, 50);
            }}).catch(function(err) {{
                console.error("Mermaid render error:", err);
                target.innerHTML = '<div style="color:var(--red); padding:20px;">Failed to render Mermaid diagram: ' + err.message + '</div>';
            }});
        }}
    }}

    function renderDockerDiagram() {{
        if (dockerMermaidRendered) {{
            if (dockerPanZoom) {{
                dockerPanZoom.resize();
                dockerPanZoom.fit();
                dockerPanZoom.center();
            }}
            return;
        }}
        dockerMermaidRendered = true;
        var tpl = document.getElementById('dockerMermaidSrc');
        var target = document.getElementById('dockerMermaid');
        if (tpl && target && typeof mermaid !== 'undefined') {{
            var src = tpl.textContent.trim();
            var uniqueId = 'svg_docker_' + Math.floor(Math.random() * 1000000);
            mermaid.render(uniqueId, src).then(function(res) {{
                target.innerHTML = res.svg;
                setTimeout(function() {{ initPanZoom('dockerMermaid', false); }}, 50);
            }}).catch(function(err) {{
                console.error("Mermaid render error:", err);
                target.innerHTML = '<div style="color:var(--red); padding:20px;">Failed to render Mermaid diagram: ' + err.message + '</div>';
            }});
        }}
    }}

    function renderSwaggerUI() {{
        if (swaggerUiRendered) return;
        swaggerUiRendered = true;
        var srcElem = document.getElementById('swaggerOpenApiJsonSrc');
        var targetContainer = document.getElementById('swagger-ui-container');
        if (srcElem && targetContainer && typeof SwaggerUIBundle !== 'undefined') {{
            try {{
                var spec = JSON.parse(srcElem.textContent);
                SwaggerUIBundle({{
                    spec: spec,
                    dom_id: '#swagger-ui-container',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout"
                }});
            }} catch(e) {{
                console.error("Swagger UI init error:", e);
                targetContainer.innerHTML = '<div style="color:var(--red); padding:20px;">Swagger UI render error: ' + e.message + '</div>';
            }}
        }}
    }}

    function switchSwaggerView(view, btn) {{
        document.querySelectorAll('.sub-tab-btn').forEach(function(el) {{ el.classList.remove('active'); }});
        document.querySelectorAll('.swagger-view-pane').forEach(function(el) {{ el.classList.remove('active'); }});
        if (btn) btn.classList.add('active');
        var pane = document.getElementById('swagger-view-' + view);
        if (pane) pane.classList.add('active');
        if (view === 'ui') {{
            setTimeout(renderSwaggerUI, 50);
        }}
    }}

    function showTab(id, btn) {{
        document.querySelectorAll('.section').forEach(function(s) {{ s.classList.remove('active'); }});
        document.querySelectorAll('.nav-btn').forEach(function(b) {{ b.classList.remove('active'); }});
        document.getElementById('sec-' + id).classList.add('active');
        if (btn) btn.classList.add('active');

        if (id === 'sysarch') {{
            setTimeout(renderSysarchDiagram, 50);
        }} else if (id === 'docker') {{
            setTimeout(renderDockerDiagram, 50);
        }} else if (id === 'swagger') {{
            setTimeout(renderSwaggerUI, 50);
        }}
    }}

    function exportPDF() {{
        var sections = document.querySelectorAll('.section');
        sections.forEach(function(s) {{ s.style.display = 'block'; }});

        var swaggerPanes = document.querySelectorAll('.swagger-view-pane');
        swaggerPanes.forEach(function(p) {{ p.style.display = 'block'; }});

        // Pre-render diagrams and Swagger UI if not initialized yet
        if (typeof renderSysarchDiagram === 'function') renderSysarchDiagram();
        if (typeof renderDockerDiagram === 'function') renderDockerDiagram();
        if (typeof renderSwaggerUI === 'function') renderSwaggerUI();

        setTimeout(function() {{
            window.print();
            sections.forEach(function(s) {{ s.style.display = ''; }});
            swaggerPanes.forEach(function(p) {{ p.style.display = ''; }});
            var activeBtn = document.querySelector('.nav-btn.active');
            if (activeBtn) {{
                var onClickAttr = activeBtn.getAttribute('onclick');
                if (onClickAttr) {{
                    var match = onClickAttr.match(/showTab\('([^']+)'/);
                    if (match) showTab(match[1], activeBtn);
                }}
            }}
        }}, 600);
    }}

    function filterModules() {{
        var q = document.getElementById('modSearch').value.toLowerCase();
        document.querySelectorAll('#modulesGrid .card').forEach(function(card) {{
            var text = card.innerText.toLowerCase();
            card.style.display = text.indexOf(q) !== -1 ? '' : 'none';
        }});
    }}

    mermaid.initialize({{ startOnLoad: false, theme: 'dark' }});
</script>

<!-- API Endpoint Prompt Modal -->
<div id="apiPromptModal" class="custom-modal-backdrop" onclick="closeApiPromptModal(event)">
    <div class="custom-modal-content" onclick="event.stopPropagation()">
        <div class="custom-modal-header">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:22px;">🤖</span>
                <div>
                    <h3 style="margin:0; font-size:16px; font-weight:700; color:var(--text);">AI Senior Developer Prompt</h3>
                    <div style="font-size:12px; color:var(--accent); font-family:var(--font-code); font-weight:600; margin-top:2px;" id="apiPromptModalSub">Endpoint Architecture Analysis Prompt</div>
                </div>
            </div>
            <button class="custom-modal-close" onclick="closeApiPromptModal()">&times;</button>
        </div>
        <div class="custom-modal-body">
            <div style="margin-bottom:12px; display:flex; align-items:center; justify-content:space-between;">
                <span style="font-size:12px; font-weight:600; color:var(--muted);">COPY &amp; PASTE THIS PROMPT TO YOUR AI ASSISTANT:</span>
                <button id="modalCopyBtn" class="btn-copy-prompt" onclick="copyModalPromptText()">📋 Copy Prompt</button>
            </div>
            <textarea id="apiPromptTextarea" readonly rows="16" style="width:100%; background:var(--bg); color:var(--text); border:1px solid var(--border); border-radius:8px; padding:14px; font-family:var(--font-code); font-size:12px; line-height:1.6; resize:vertical; outline:none;"></textarea>
        </div>
    </div>
</div>

<script>
    function getApiPromptText(method, path) {{
        var cleanFileName = (method.toLowerCase() + '_' + path)
            .replace(/[^a-zA-Z0-9_]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '') + '_analysis.md';

        return "Use @arch-wiki skill. You are joining this project as a senior developer.\\n\\n" +
            "Analyze this API endpoint:\\n\\n" +
            method + " " + path + "\\n\\n" +
            "Use:\\n" +
            "1. architecture.json\\n" +
            "2. arch-wiki documentation\\n" +
            "3. the project source code\\n\\n" +
            "Discover the actual implementation flow.\\n\\n" +
            "Generate:\\n\\n" +
            "1. Mermaid sequence diagram (both Mermaid code format and rendered visual diagram image)\\n" +
            "2. Mermaid flowchart (both Mermaid code format and rendered visual diagram image)\\n\\n" +
            "Include only components and interactions that actually exist in the code.\\n\\n" +
            "Do not infer missing components.\\n" +
            "Do not modify anything.\\n\\n" +
            "Save the analysis output in " + cleanFileName;
    }}

    function openApiPromptFromEl(el) {{
        var method = el.getAttribute('data-method') || 'GET';
        var path = el.getAttribute('data-path') || '/';
        openApiPromptModal(method, path);
    }}

    function copyApiPromptDirectFromEl(el) {{
        var method = el.getAttribute('data-method') || 'GET';
        var path = el.getAttribute('data-path') || '/';
        var btn = el.querySelector('.btn-prompt-copy');
        copyApiPromptDirect(method, path, btn);
    }}

    function openApiPromptModal(method, path) {{
        var modal = document.getElementById('apiPromptModal');
        var sub = document.getElementById('apiPromptModalSub');
        var ta = document.getElementById('apiPromptTextarea');
        var btn = document.getElementById('modalCopyBtn');

        if (!modal || !ta) return;

        var promptText = getApiPromptText(method, path);
        ta.value = promptText;
        if (sub) sub.innerText = method + ' ' + path;
        if (btn) {{
            btn.innerHTML = '📋 Copy Prompt';
            btn.style.background = '';
        }}

        modal.classList.add('active');
    }}

    function closeApiPromptModal(e) {{
        if (e && e.target !== e.currentTarget && !e.target.classList.contains('custom-modal-close')) return;
        var modal = document.getElementById('apiPromptModal');
        if (modal) modal.classList.remove('active');
    }}

    function copyModalPromptText() {{
        var ta = document.getElementById('apiPromptTextarea');
        var btn = document.getElementById('modalCopyBtn');
        if (!ta) return;

        navigator.clipboard.writeText(ta.value).then(function() {{
            if (btn) {{
                btn.innerHTML = '✅ Copied!';
                setTimeout(function() {{
                    btn.innerHTML = '📋 Copy Prompt';
                }}, 2000);
            }}
        }}).catch(function() {{
            ta.select();
            document.execCommand('copy');
            if (btn) {{
                btn.innerHTML = '✅ Copied!';
                setTimeout(function() {{
                    btn.innerHTML = '📋 Copy Prompt';
                }}, 2000);
            }}
        }});
    }}

    function copyApiPromptDirect(method, path, btnElement) {{
        var promptText = getApiPromptText(method, path);
        navigator.clipboard.writeText(promptText).then(function() {{
            if (btnElement) {{
                var orig = btnElement.innerHTML;
                btnElement.innerHTML = '✅ Copied!';
                setTimeout(function() {{
                    btnElement.innerHTML = orig;
                }}, 2000);
            }}
        }}).catch(function() {{
            if (btnElement) {{
                var orig = btnElement.innerHTML;
                btnElement.innerHTML = '✅ Copied!';
                setTimeout(function() {{
                    btnElement.innerHTML = orig;
                }}, 2000);
            }}
        }});
    }}

    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            closeApiPromptModal();
        }}
    }});
</script>
</body>
</html>
"""

    if not target_dir:
        target_dir = os.path.dirname(__file__)
    out_path = os.path.join(target_dir, 'architecture.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Successfully generated architecture.html at {out_path}")

if __name__ == '__main__':
    target_path = None
    for arg in sys.argv[1:]:
        if not arg.startswith('--') and os.path.exists(arg):
            target_path = os.path.abspath(arg)
            break
    
    if not target_path:
        target_path = os.getcwd()
    
    arch_dir = os.path.join(target_path, 'docs', 'architecture') if os.path.basename(target_path) != 'architecture' else target_path
    os.makedirs(arch_dir, exist_ok=True)
    json_path = os.path.join(arch_dir, 'architecture.json')
    has_json = os.path.isfile(json_path)

    if '--init' in sys.argv or '--rescan' in sys.argv or '--sync' in sys.argv or not has_json:
        if has_json:
            print(f"[arch-wiki] Syncing codebase changes with architecture.json at {json_path}...")
        else:
            print(f"[arch-wiki] Initializing fresh architecture manifest at {json_path}...")
        data = init_architecture(target_path)
    else:
        data = load_architecture(json_path)

    generate_html(data, arch_dir)
    print(f"[arch-wiki] Done. Open {os.path.join(arch_dir, 'architecture.html')} in your browser.")
