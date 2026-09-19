"""Scanner accuracy tests against the small fixture projects in tests/fixtures/.

Express and FastAPI assertions pin the existing behaviour; the Spring fixture
exercises the Gradle Kotlin-DSL / multi-path / @Query / docker-compose fixes.
"""
import json
import os
from html import unescape as html_unescape

import pytest

from conftest import endpoint_index, endpoints


# ---------------------------------------------------------------- Express

def test_express_detection_and_routes(build_html, fixture_project):
    root = fixture_project('express')
    data = build_html.init_architecture(root)

    assert build_html._detect_fw(root) == 'express'
    assert data['meta']['techStack']['framework'] == 'Express.js'
    assert sorted(m['id'] for m in data['modules']) == ['auth', 'users']
    assert sorted(endpoints(data)) == sorted([
        ('POST', '/api/v1/auth/login'), ('POST', '/api/v1/auth/refresh'), ('GET', '/api/v1/auth/me'),
        ('GET', '/api/v1/users'), ('GET', '/api/v1/users/:id'),
        ('POST', '/api/v1/users'), ('DELETE', '/api/v1/users/:id'),
    ])
    idx = endpoint_index(data)
    assert idx[('GET', '/api/v1/users/:id')]['permission'] == 'users:read'
    assert data['permissions']['catalog'] == ['authenticated', 'users:delete', 'users:read', 'users:write']
    # Express keeps the placeholder SQL catalog (one entry per endpoint).
    assert len(data['sqlQueries']) == 7
    assert os.path.isfile(os.path.join(root, 'docs', 'architecture', 'architecture.json'))


def test_express_docker_block_style(build_html, fixture_project):
    root = fixture_project('express')
    infra, diagram = build_html._scan_docker(root)
    assert [(s['id'], s['type'], s['port']) for s in infra] == [
        ('api', 'app', 3000), ('postgres', 'database', 5432), ('redis', 'cache', 6379)]
    assert sorted((e['from'], e['to']) for e in diagram['edges']) == [('api', 'postgres'), ('api', 'redis')]


# ---------------------------------------------------------------- FastAPI

def test_fastapi_detection_and_routes(build_html, fixture_project):
    root = fixture_project('fastapi')
    data = build_html.init_architecture(root)

    assert build_html._detect_fw(root) == 'fastapi'
    assert sorted(endpoints(data)) == sorted([
        ('GET', '/api/main/health'),
        ('GET', '/api/items'), ('GET', '/api/items/{item_id}'), ('POST', '/api/items'),
        ('GET', '/api/orders'), ('DELETE', '/api/orders/{order_id}'),
    ])
    assert len(data['sqlQueries']) == 6
    assert data['infrastructure'] == []


# ---------------------------------------------------------------- HTML

def test_generate_html_writes_page(build_html, fixture_project, tmp_path):
    root = fixture_project('express')
    data = build_html.init_architecture(root)
    out_dir = os.path.join(root, 'docs', 'architecture')
    build_html.generate_html(data, out_dir)
    html = open(os.path.join(out_dir, 'architecture.html'), encoding='utf-8').read()
    assert '<title>' in html and 'Acme Express Api' in html
    json.loads(html_unescape(html.split('id="swaggerOpenApiJsonSrc">', 1)[1].split('</code>', 1)[0]))


# ---------------------------------------------------------------- Spring / Gradle KTS

def test_spring_kts_detection_and_versions(build_html, fixture_project):
    root = fixture_project('spring-kts')
    assert build_html._detect_fw(root) == 'spring'
    assert build_html._detect_arch_type(root, 'spring') == 'microservice'  # docker-compose present
    assert build_html._gradle_includes(root) == ['billing', 'users', 'messaging']

    info = build_html._java_build_info(root)
    assert info['buildTool'] == 'gradle' and info['kotlinDsl'] is True
    assert info['buildFile'] == 'build.gradle.kts'
    assert info['javaVersion'] == '25'
    assert info['springBootVersion'] == '4.0.0'

    data = build_html.init_architecture(root)
    assert data['meta']['techStack'] == {
        'language': 'Java 25', 'framework': 'Spring Boot 4.0.0',
        'database': 'Postgres', 'auth': 'JWT / Bearer Token'}
    jdk = next(t for t in data['prerequisites']['tools'] if t['category'] == 'runtime')
    assert jdk['version'] == '>= 25'
    assert [w['name'] for w in data['workspaces']] == ['billing', 'users', 'messaging']
    assert data['workspaces'][0]['entrypoint'] == 'billing/build.gradle.kts'


def test_java_build_info_maven_and_groovy(build_html, tmp_path):
    mvn = tmp_path / 'mvn'; mvn.mkdir()
    (mvn / 'pom.xml').write_text("""<project>
      <parent><groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId><version>3.4.2</version></parent>
      <properties><java.version>21</java.version></properties></project>""")
    info = build_html._java_build_info(str(mvn))
    assert (info['buildTool'], info['javaVersion'], info['springBootVersion']) == ('maven', '21', '3.4.2')

    groovy = tmp_path / 'groovy'; groovy.mkdir()
    (groovy / 'build.gradle').write_text("""plugins {
        id 'org.springframework.boot' version '3.3.0'
    }
    sourceCompatibility = JavaVersion.VERSION_17
    """)
    info = build_html._java_build_info(str(groovy))
    assert (info['buildTool'], info['kotlinDsl'], info['javaVersion'], info['springBootVersion']) == ('gradle', False, '17', '3.3.0')
    assert build_html._detect_fw(str(groovy)) == 'spring'

    catalog = tmp_path / 'catalog'; (catalog / 'gradle').mkdir(parents=True)
    (catalog / 'build.gradle.kts').write_text('plugins { alias(libs.plugins.spring.boot) }\n')
    (catalog / 'gradle' / 'libs.versions.toml').write_text('[versions]\nspring-boot = "3.5.1"\njava = "21"\n')
    info = build_html._java_build_info(str(catalog))
    assert (info['javaVersion'], info['springBootVersion']) == ('21', '3.5.1')


def test_spring_routes_multi_path_and_permissions(build_html, fixture_project):
    root = fixture_project('spring-kts')
    mods = {m['id']: m for m in build_html._scan_java_spring(root)}
    assert sorted(mods) == ['billing', 'users']

    billing, users = mods['billing'], mods['users']
    # Module basePath is the common prefix of its controllers; endpoint paths are relative to it.
    assert billing['basePath'] == '/api' and users['basePath'] == '/api'
    assert billing['description'].startswith('Invoice lifecycle and lookup')  # from @Tag

    data = {'modules': [billing, users]}
    got = sorted(endpoints(data))
    inv = ['/api/v1/invoices', '/api/v2/invoices']
    expected = []
    for b in inv:
        expected += [('GET', f'{b}/customer/{{customerId}}'), ('GET', f'{b}/{{id}}'), ('GET', f'{b}/by-id/{{id}}'),
                     ('POST', b), ('POST', f'{b}/{{id}}/void'), ('PUT', f'{b}/{{id}}/void')]
    expected += [('GET', '/api/v1/payments'), ('GET', '/api/v1/payments/{id}'), ('POST', '/api/v1/payments/{id}/refund'),
                 ('GET', '/api/public/ping'), ('GET', '/api/v1/users'), ('GET', '/api/v1/users/me'),
                 ('DELETE', '/api/v1/users/{id}'), ('PATCH', '/api/v1/users/{id}/roles')]
    assert got == sorted(expected)
    assert len(got) == 20

    idx = endpoint_index(data)
    # path= after produces=, @PreAuthorize before the mapping, @Operation summary
    ep = idx[('GET', '/api/v1/invoices/customer/{customerId}')]
    assert ep['description'] == 'List invoices for a customer'
    assert ep['permission'] == 'billing.invoice.view'
    assert ep['permissionExpression'] == "hasAuthority('billing.invoice.view')"
    assert ep['objectLevel'] is False
    assert ep['handler'] == 'InvoiceController.byCustomer'
    # value={…} array, @PreAuthorize AFTER the mapping, @Operation after that
    ep = idx[('GET', '/api/v2/invoices/by-id/{id}')]
    assert ep['description'] == 'Get one invoice'
    assert ep['permission'] == 'billing.invoice.view'
    assert ep['objectLevel'] is True
    assert ep['permissionExpression'].startswith("hasAuthority('billing.invoice.view') and @billingAuth")
    # @RequestMapping with method={POST, PUT} and produces=
    assert idx[('PUT', '/api/v1/invoices/{id}/void')]['permission'] is None
    # class-level @PreAuthorize applies to un-annotated methods, method-level overrides
    assert idx[('GET', '/api/v1/payments/{id}')]['permission'] == 'billing.payment.view'
    assert idx[('POST', '/api/v1/payments/{id}/refund')]['permission'] == 'ROLE_FINANCE'
    # class @RequestMapping(path=…, produces=…)
    assert idx[('GET', '/api/v1/users/me')]['permission'] is None
    assert idx[('GET', '/api/public/ping')]['auth'] is False
    assert idx[('GET', '/api/v1/users')]['auth'] is True


def test_spring_scanner_ignores_comments_and_resolves_constants(build_html, tmp_path):
    src = tmp_path / 'src' / 'main' / 'java'
    src.mkdir(parents=True)
    (src / 'Paths.java').write_text('public final class Paths { public static final String ORDERS = "/api/orders"; }')
    (src / 'OrderController.java').write_text('''
        @RestController
        @RequestMapping(Paths.ORDERS)
        public class OrderController {
            private static final String BY_ID = "/{id}";
            // @GetMapping("/commented-out")
            /* @PostMapping("/also-commented") */
            @GetMapping(BY_ID) public Object one(@PathVariable Long id) { return "@GetMapping(\\"/in-a-string\\")"; }
            @DeleteMapping(value = BY_ID, produces = "application/json") public void del(@PathVariable Long id) {}
        }
    ''')
    mods = build_html._scan_java_spring(str(tmp_path), arch_type='monolith')
    assert len(mods) == 1
    assert mods[0]['basePath'] == '/api/orders'
    assert sorted((e['method'], e['path']) for e in mods[0]['endpoints']) == [('DELETE', '/{id}'), ('GET', '/{id}')]


def test_spring_no_class_mapping_has_no_fabricated_base(build_html, tmp_path):
    src = tmp_path / 'src' / 'main' / 'java'
    src.mkdir(parents=True)
    (src / 'HealthController.java').write_text('''
        @RestController
        public class HealthController {
            @GetMapping("/actuator/ping") public String ping() { return "ok"; }
        }
    ''')
    mods = build_html._scan_java_spring(str(tmp_path), arch_type='monolith')
    assert mods[0]['basePath'] == '/'
    assert mods[0]['endpoints'][0]['path'] == '/actuator/ping'


# ---------------------------------------------------------------- SQL

def test_spring_sql_catalog_is_extracted_not_invented(build_html, fixture_project):
    root = fixture_project('spring-kts')
    data = build_html.init_architecture(root)
    q = {x['function']: x for x in data['sqlQueries']}
    assert len(data['sqlQueries']) == 6
    assert all(x['endpoints'] == [] for x in data['sqlQueries'])
    assert all(x['module'] == 'Billing Service' for x in data['sqlQueries'])

    assert q['InvoiceRepository.findByCustomer()']['queryType'] == 'jpql'
    assert q['InvoiceRepository.findByCustomer()']['tables'] == ['Invoice']          # i.customer path skipped
    native = q['InvoiceRepository.findWithCustomerByStatus()']
    assert native['queryType'] == 'native'
    assert native['tables'] == ['billing.invoice', 'billing.customer']
    assert native['sql'].startswith('SELECT inv.*, cust.name\nFROM billing.invoice inv')  # text block de-indented
    assert q['InvoiceRepository.voidById()']['tables'] == ['billing.invoice']

    chain = q['PaymentReportDao.monthlyTotals()']
    assert chain['queryType'] == 'sql'
    assert chain['tables'] == ['billing.payment']                                    # EXTRACT(... FROM paid_at) ignored
    assert 'GROUP BY 1 ORDER BY 1' in chain['sql']
    # dense single-line `@Transactional public int archive(...){...} public String label(){...}`
    assert q['PaymentReportDao.archive()']['tables'] == ['billing.payment_archive', 'billing.payment']
    assert q['PaymentReportDao.purge()']['sql'].startswith('DELETE FROM billing.payment_archive')
    assert 'PaymentReportDao.label()' not in q
    assert all('not sql' not in x['sql'] for x in data['sqlQueries'])


def test_placeholder_sql_flag_restores_legacy_catalog(build_html, fixture_project):
    root = fixture_project('spring-kts')
    data = build_html.init_architecture(root, placeholder_sql=True)
    assert len(data['sqlQueries']) == 20  # one per endpoint
    assert all(x['endpoints'] for x in data['sqlQueries'])


def test_sql_field_constants_and_entity_manager(build_html, tmp_path):
    src = tmp_path / 'src' / 'main' / 'java'
    src.mkdir(parents=True)
    (src / 'ReportDao.java').write_text('''
        @Repository
        public class ReportDao {
            private static final String TOTALS = "SELECT customer_id, SUM(total) FROM invoice GROUP BY customer_id";
            @PersistenceContext private EntityManager em;

            public List<Object[]> totals() { return em.createNativeQuery(TOTALS).getResultList(); }

            public List<Invoice> open() {
                return em.createQuery("SELECT i FROM Invoice i WHERE i.status = 'OPEN'", Invoice.class).getResultList();
            }

            public String greeting() { return "select is not a query here"; }
        }
    ''')
    qs = build_html._scan_sql_java(str(tmp_path))
    by_fn = {q['function']: q for q in qs}
    assert set(by_fn) == {'ReportDao.TOTALS', 'ReportDao.open()'}
    assert by_fn['ReportDao.TOTALS']['tables'] == ['invoice']
    assert by_fn['ReportDao.open()']['queryType'] == 'jpql'


# ---------------------------------------------------------------- docker-compose

EXPECTED_SPRING_SERVICES = [
    ('api', 'app', 8081), ('postgres', 'database', 5432), ('kafka', 'queue', 9092),
    ('keycloak', 'auth', 8080), ('mailpit', 'mail', 8025), ('nginx', 'proxy', 80)]


def test_docker_yaml_ports_profiles_depends_and_env_edges(build_html, fixture_project):
    pytest.importorskip('yaml')   # env-derived edges / port lists need the YAML parser
    root = fixture_project('spring-kts')
    infra, diagram = build_html._scan_docker(root)
    assert [(s['id'], s['type'], s['port']) for s in infra] == EXPECTED_SPRING_SERVICES
    by_id = {s['id']: s for s in infra}
    assert by_id['mailpit']['optional'] is True and by_id['mailpit']['profiles'] == ['dev']
    assert by_id['kafka']['ports'] == [9092, 9093]           # short + long port syntax
    assert 'optional' not in by_id['api']

    edges = {(e['from'], e['to']): e for e in diagram['edges']}
    assert sorted(edges) == [('api', 'kafka'), ('api', 'keycloak'), ('api', 'mailpit'), ('api', 'postgres'),
                             ('keycloak', 'postgres'), ('nginx', 'api'), ('nginx', 'keycloak')]
    assert edges[('api', 'postgres')]['kind'] == 'depends_on'        # map-form depends_on
    assert edges[('api', 'postgres')]['label'] == 'SPRING_DATASOURCE_URL :5432'   # runtime label preferred
    assert edges[('api', 'kafka')]['label'] == 'SPRING_KAFKA_BOOTSTRAP_SERVERS :9092'
    assert edges[('nginx', 'api')] == {'from': 'nginx', 'to': 'api', 'label': 'UPSTREAM :8081', 'kind': 'depends_on', 'env': 'UPSTREAM'}
    assert edges[('api', 'keycloak')] == {'from': 'api', 'to': 'keycloak', 'label': 'KEYCLOAK_ISSUER_URI :8080', 'kind': 'env', 'env': 'KEYCLOAK_ISSUER_URI'}
    assert edges[('api', 'mailpit')]['label'] == 'MAIL_HOST'
    assert edges[('keycloak', 'postgres')]['label'] == ''            # no env hint → plain depends_on
    optional_nodes = [n['id'] for n in diagram['nodes'] if n.get('optional')]
    assert optional_nodes == ['mailpit']


def test_docker_line_parser_fallback_without_pyyaml(build_html, fixture_project, monkeypatch):
    monkeypatch.setattr(build_html, '_yaml', None)
    root = fixture_project('spring-kts')
    infra, diagram = build_html._scan_docker(root)
    assert [(s['id'], s['type'], s['port']) for s in infra] == EXPECTED_SPRING_SERVICES
    assert sorted((e['from'], e['to']) for e in diagram['edges']) == [
        ('api', 'kafka'), ('api', 'postgres'), ('keycloak', 'postgres'), ('nginx', 'api'), ('nginx', 'keycloak')]
    root = fixture_project('express')
    infra, _ = build_html._scan_docker(root)
    assert [(s['id'], s['port']) for s in infra] == [('api', 3000), ('postgres', 5432), ('redis', 6379)]


def test_compose_port_forms(build_html):
    p = build_html._compose_port
    assert p(5432) == 5432
    assert p('5432') == 5432
    assert p('5432:5432') == 5432
    assert p('127.0.0.1:8080:80') == 8080
    assert p('[::1]:8443:443') == 8443
    assert p('8080-8081:80-81') == 8080
    assert p('9092:9092/udp') == 9092
    assert p({'target': 9093, 'published': 19093}) == 19093
    assert p({'target': 9093}) == 9093
    assert p({'target': 80, 'published': '8000-8001'}) == 8000


def test_infer_service_type_from_image(build_html):
    t = build_html._infer_service_type
    assert t('idp', 'quay.io/keycloak/keycloak:26.0') == 'auth'
    assert t('broker', 'apache/kafka:3.9.0') == 'queue'
    assert t('mail', 'axllent/mailpit') == 'mail'
    assert t('edge', 'nginx:1.27') == 'proxy'
    assert t('pbx', 'andrius/asterisk') == 'voice'
    assert t('metrics', 'prom/prometheus') == 'monitoring'
    assert t('topics', 'provectuslabs/kafka-ui') == 'monitoring'
    assert t('db', '') == 'database'
    assert t('worker', 'ghcr.io/acme/worker:1') == 'app'


def test_docker_diagram_html_has_styles_for_new_types(build_html, fixture_project):
    pytest.importorskip('yaml')   # env-derived edges / port lists need the YAML parser
    root = fixture_project('spring-kts')
    data = build_html.init_architecture(root)
    out_dir = os.path.join(root, 'docs', 'architecture')
    build_html.generate_html(data, out_dir)
    page = open(os.path.join(out_dir, 'architecture.html'), encoding='utf-8').read()
    docker_src = page.split('id="dockerMermaidSrc">', 1)[1].split('</script>', 1)[0]
    assert 'classDef auth' in docker_src and 'classDef mail' in docker_src
    assert 'class keycloak auth;' in docker_src
    assert 'class mailpit mail;' in docker_src
    assert 'style mailpit stroke-dasharray' in docker_src
    assert 'api -->|"KEYCLOAK_ISSUER_URI :8080"| keycloak' in docker_src


# ---------------------------------------------------------------- permissions

def test_normalize_spel(build_html):
    n = build_html._normalize_spel
    assert n("hasAuthority('x.view') and @auth.canAccess(authentication, #id)") == {
        'permission': 'x.view', 'objectLevel': True, 'auth': True}
    assert n("hasAnyAuthority('a', 'b')")['permission'] == 'a | b'
    assert n("hasRole('ADMIN')")['permission'] == 'ROLE_ADMIN'
    assert n("hasAnyRole('ROLE_A', 'B')")['permission'] == 'ROLE_A | ROLE_B'
    assert n('isAuthenticated()') == {'permission': None, 'objectLevel': False, 'auth': True}
    assert n('permitAll()') == {'permission': None, 'objectLevel': False, 'auth': False}
    assert n('@userAuth.isSelfOrAdmin(#id)') == {'permission': 'userAuth.isSelfOrAdmin', 'objectLevel': True, 'auth': True}
    assert n("hasPermission(#id, 'Invoice', 'read')")['objectLevel'] is True
    assert n(None) == {'permission': None, 'objectLevel': False, 'auth': None}


def test_permission_catalog_has_clean_slugs_and_public_count(build_html, fixture_project):
    root = fixture_project('spring-kts')
    data = build_html.init_architecture(root)
    assert data['permissions']['catalog'] == [
        'ROLE_ADMIN', 'ROLE_FINANCE', 'authenticated', 'billing.admin', 'billing.invoice.create',
        'billing.invoice.view', 'billing.payment.view', 'public', 'userAuth.isSelfOrAdmin']
    assert not any('(' in slug for slug in data['permissions']['catalog'])
    view = next(d for d in data['permissions']['details'] if d['slug'] == 'billing.invoice.view')
    assert view['objectLevel'] is True
    assert sorted(view['expressions']) == [
        "hasAuthority('billing.invoice.view')",
        "hasAuthority('billing.invoice.view') and @billingAuth.canAccess(authentication, #id)"]
    assert sum(1 for e in view['endpoints'] if e.get('objectLevel')) == 4
    idx = endpoint_index(data)
    assert idx[('GET', '/api/v1/users')]['auth'] is True          # isAuthenticated()
    assert idx[('GET', '/api/v1/users')]['permission'] is None

    out_dir = os.path.join(root, 'docs', 'architecture')
    build_html.generate_html(data, out_dir)
    page = open(os.path.join(out_dir, 'architecture.html'), encoding='utf-8').read()
    # 1 public route (/api/public/ping) + 3 Actuator system endpoints
    assert '<div class="stat-num">4</div><div class="stat-lbl">Public Endpoints</div>' in page
    assert '<div class="stat-num">19</div><div class="stat-lbl">Authenticated Endpoints</div>' in page
    assert '<div class="stat-num">5</div><div class="stat-lbl">Object-Level Checks</div>' in page
    assert 'object-level' in page


# ---------------------------------------------------------------- override hook

def test_arch_overrides_hook_is_applied(build_html, fixture_project):
    root = fixture_project('spring-kts')
    arch_dir = os.path.join(root, 'docs', 'architecture')
    os.makedirs(arch_dir, exist_ok=True)
    with open(os.path.join(arch_dir, 'arch_overrides.py'), 'w') as f:
        f.write('''
import build_html
def apply(data, root):
    assert data["modules"] and "sqlQueries" in data
    data["meta"]["techStack"]["auth"] = "Keycloak OIDC"
    data["modules"] = [m for m in data["modules"] if m["id"] == "users"]
    for ep in data["modules"][0]["endpoints"]:
        ep["permission"] = "users.any"
        ep["auth"] = True
    data["permissions"] = build_html.build_permissions(data["modules"])
    data["sqlQueries"][0]["endpoints"] = [{"method": "GET", "path": "/api/v1/users"}]
    data["hookRoot"] = root
    return data
''')
    data = build_html.init_architecture(root)
    assert data['meta']['techStack']['auth'] == 'Keycloak OIDC'
    assert [m['id'] for m in data['modules']] == ['users']
    assert data['permissions']['catalog'] == ['users.any']
    assert data['swaggerSchemas']['matchStatus'] == 'Verified Parity (5/5 Endpoints)'
    assert data['sqlQueries'][0]['endpoints'] == [{'method': 'GET', 'path': '/api/v1/users'}]
    assert data['hookRoot'] == root
    written = json.load(open(os.path.join(arch_dir, 'architecture.json')))
    assert written['permissions']['catalog'] == ['users.any']


def test_arch_overrides_returning_none_keeps_data_and_errors_propagate(build_html, fixture_project):
    import pytest
    root = fixture_project('express')
    arch_dir = os.path.join(root, 'docs', 'architecture')
    os.makedirs(arch_dir, exist_ok=True)
    hook = os.path.join(arch_dir, 'arch_overrides.py')
    with open(hook, 'w') as f:
        f.write('def apply(data, root):\n    data["meta"]["version"] = "9.9.9"\n')
    assert build_html.init_architecture(root)['meta']['version'] == '9.9.9'
    with open(hook, 'w') as f:
        f.write('def apply(data, root):\n    raise ValueError("bad catalog")\n')
    with pytest.raises(ValueError):
        build_html.init_architecture(root)


def test_example_override_hook_runs(build_html, fixture_project):
    import importlib.util
    root = fixture_project('spring-kts')
    os.makedirs(os.path.join(root, 'docs'), exist_ok=True)
    with open(os.path.join(root, 'docs', 'permissions.json'), 'w') as f:
        json.dump([{'slug': 'billing.invoice.view', 'pages': ['Invoices', 'Customer Detail']}], f)
    fe = os.path.join(root, 'frontend', 'src', 'pages', 'invoices')
    os.makedirs(fe)
    with open(os.path.join(fe, 'api.ts'), 'w') as f:
        f.write("export const load = () => api.get('/api/v1/payments');\n")
    spec = importlib.util.spec_from_file_location('arch_overrides_example',
                                                  os.path.join(os.path.dirname(build_html.__file__), 'arch_overrides.example.py'))
    example = importlib.util.module_from_spec(spec); spec.loader.exec_module(example)
    data = example.apply(build_html.init_architecture(root), root)
    idx = endpoint_index(data)
    assert idx[('GET', '/api/v1/payments')]['pages'] == ['Invoices']
    pay = next(d for d in data['permissions']['details'] if d['slug'] == 'billing.payment.view')
    assert pay['adminPages'] == ['Invoices']
    inv = next(d for d in data['permissions']['details'] if d['slug'] == 'billing.invoice.view')
    assert inv['adminPages'] == ['Invoices', 'Customer Detail']


# ---------------------------------------------------------------- template details

def test_spring_template_defaults_and_messaging(build_html, fixture_project):
    root = fixture_project('spring-kts')
    data = build_html.init_architecture(root)

    sw = data['swaggerSchemas']
    assert (sw['openapi'], sw['servedAt'], sw['swaggerUi']) == ('3.1.0', '/v3/api-docs', '/swagger-ui.html')
    assert sw['servers'][0]['url'] == 'http://localhost:8081'          # server.port from application.yml

    steps = {s['title']: s['command'] for s in data['prerequisites']['setupSteps']}
    assert steps['Build Gradle Projects'] == './gradlew build -x test'
    assert steps['Launch Development Server'] == './gradlew bootRun'
    assert not any('mvnw' in c for c in steps.values())
    assert any(t['name'].startswith('Gradle') for t in data['prerequisites']['tools'])

    msg = data['messaging']
    assert [(l['handler'], l['topics'], l['groupId']) for l in msg['listeners']] == [
        ('InvoiceEventsListener.onInvoice()', ['billing.invoice.created', 'billing.invoice.voided'], 'messaging'),
        ('InvoiceEventsListener.onPayment()', ['${acme.kafka.topics.payments}'], 'messaging')]
    assert msg['producers'] == [
        {'broker': 'kafka', 'topic': 'billing.notifications', 'handler': 'NotificationPublisher.publish()',
         'file': 'messaging/src/main/java/com/acme/messaging/NotificationPublisher.java'},
        {'broker': 'kafka', 'topic': None, 'dynamic': True, 'expression': 'record',
         'handler': 'OutboxPublisher.relay()',
         'file': 'messaging/src/main/java/com/acme/messaging/OutboxPublisher.java'}]

    out_dir = os.path.join(root, 'docs', 'architecture')
    build_html.generate_html(data, out_dir)
    page = open(os.path.join(out_dir, 'architecture.html'), encoding='utf-8').read()
    assert 'AHMED EMAD' not in page
    assert 'Spring Kts · generated by arch-wiki' in page
    assert '<code>http://localhost:8081</code>' in page
    assert 'curl -X GET &quot;http://localhost:8081/api/public/ping&quot;' in page
    assert 'OpenAPI 3.1 API Specification' in page and '<code>/v3/api-docs</code>' in page
    assert '<code>/swagger-ui.html</code>' in page
    assert 'id="sec-messaging"' in page and 'billing.invoice.created' in page
    # SQL catalog is embedded as JSON and rendered lazily — no pre-rendered cards
    blob = page.split('id="sqlCatalogData">', 1)[1].split('</script>', 1)[0]
    assert len(json.loads(blob)) == 6
    assert page.count('SELECT inv.*, cust.name') == 1                  # only inside the JSON blob
    spec = json.loads(html_unescape(page.split('id="swaggerOpenApiJsonSrc">', 1)[1].split('</code>', 1)[0]))
    assert spec['openapi'] == '3.1.0'
    assert spec['servers'][0]['url'] == 'http://localhost:8081'


def test_core_layer_security_names_build_file(build_html, tmp_path):
    src = tmp_path / 'src' / 'main' / 'java'
    src.mkdir(parents=True)
    (tmp_path / 'build.gradle.kts').write_text('plugins { id("org.springframework.boot") version "3.5.0" }\n')
    (src / 'SecurityConfig.java').write_text('@Configuration @EnableWebSecurity public class SecurityConfig {}')
    core = build_html._scan_core_layer(str(tmp_path), 'spring', 'build.gradle.kts')
    assert core['security'][0] == {'name': 'Spring Security & OAuth2', 'file': 'build.gradle.kts',
                                   'description': 'Framework OAuth2 Resource Server & JWT verification layer'}


def test_express_and_fastapi_template_defaults_unchanged(build_html, fixture_project):
    for name in ('express', 'fastapi'):
        data = build_html.init_architecture(fixture_project(name))
        sw = data['swaggerSchemas']
        assert (sw['openapi'], sw['servedAt'], sw['servers'][0]['url']) == ('3.0.0', '/api/docs', 'http://localhost:3000')
        assert data['messaging'] == {'listeners': [], 'producers': []}


# ---------------------------------------------------------------- follow-up findings (Orbit run)

def test_sql_tables_ignore_row_locks_and_cte_names(build_html):
    t = build_html._sql_tables
    assert t("SELECT * FROM outbox_event WHERE status = 'NEW' ORDER BY id FOR UPDATE SKIP LOCKED") == ['outbox_event']
    assert t("SELECT id FROM job FOR UPDATE NOWAIT") == ['job']
    assert t("SELECT id FROM job j JOIN run r ON r.job_id = j.id FOR UPDATE OF j SKIP LOCKED") == ['job', 'run']
    assert t("""WITH candidates AS (SELECT id FROM invoice WHERE due < now()),
                     paid (id) AS (SELECT invoice_id FROM payment)
                UPDATE invoice SET status = 'LATE' FROM candidates WHERE invoice.id = candidates.id""") == ['invoice', 'payment']
    assert t("WITH RECURSIVE tree AS (SELECT * FROM org UNION ALL SELECT o.* FROM org o JOIN tree t ON o.parent = t.id) SELECT * FROM tree") == ['org']


def test_messaging_producer_via_template_field(build_html, tmp_path):
    src = tmp_path / 'src' / 'main' / 'java'; src.mkdir(parents=True)
    (src / 'Bus.java').write_text("""
        @Service public class Bus {
            private static final String TOPIC = "orders.placed";
            @Autowired private KafkaTemplate<String, Object> producer;
            private final RabbitTemplate rabbit;
            public void placed(Object o) { producer.send(TOPIC, o); }
            public void notify(Object o) { rabbit.convertAndSend("notify.exchange", "email", o); }
            public void raw(String topic, Object o) { producer.send(topic, o); }
        }""")
    prods = build_html._scan_messaging_java(str(tmp_path))['producers']
    assert [(p['broker'], p['topic'], p.get('dynamic'), p['handler']) for p in prods] == [
        ('kafka', 'orders.placed', None, 'Bus.placed()'),
        ('rabbitmq', 'notify.exchange/email', None, 'Bus.notify()'),
        ('kafka', None, True, 'Bus.raw()')]
    assert prods[2]['expression'] == 'topic'


def test_meta_version_from_build_files(build_html, fixture_project, tmp_path):
    root = fixture_project('spring-kts')
    assert build_html.init_architecture(root)['meta']['version'] == '0.1.0'                          # build.gradle.kts
    assert build_html.init_architecture(fixture_project('express'))['meta']['version'] == '1.0.0'      # package.json
    (tmp_path / 'spring-kts' / 'VERSION').write_text('v2.3.4\n')
    assert build_html.init_architecture(root)['meta']['version'] == '2.3.4'                          # VERSION wins
    mvn = tmp_path / 'mvn'; mvn.mkdir()
    (mvn / 'pom.xml').write_text('<project><parent><artifactId>spring-boot-starter-parent</artifactId><version>3.4.2</version></parent>'
                                 '<artifactId>x</artifactId><version>7.0.0-SNAPSHOT</version></project>')
    assert build_html._project_version(str(mvn), 'spring') == '7.0.0-SNAPSHOT'
    # the helper is self-contained: package.json and a default, never None
    js = tmp_path / 'js'; js.mkdir()
    (js / 'package.json').write_text('{"name": "x", "version": "2.5.0"}')
    assert build_html._project_version(str(js), 'express') == '2.5.0'
    empty = tmp_path / 'empty'; empty.mkdir()
    assert build_html._project_version(str(empty), 'spring') == '1.0.0'
    assert build_html._project_version(str(empty), 'express', default='0.0.0') == '0.0.0'


def test_migration_step_only_invents_task_with_plugin(build_html, tmp_path):
    def steps(build):
        d = tmp_path / build[0]; d.mkdir()
        (d / 'build.gradle.kts').write_text(build[1])
        info = build_html._java_build_info(str(d))
        pre = build_html._scan_prerequisites(str(d), 'spring', [], [], info)
        return next(s['command'] for s in pre['setupSteps'] if s['title'].startswith('Run Schema'))
    boot_only = steps(('a', 'dependencies { implementation("org.flywaydb:flyway-core") }'))
    assert boot_only.startswith('#') and 'flywayMigrate' not in boot_only
    with_plugin = steps(('b', 'plugins { id("org.flywaydb.flyway") version "10.0.0" }\ndependencies { implementation("org.flywaydb:flyway-core") }'))
    assert with_plugin == './gradlew flywayMigrate'
    liqui = steps(('c', 'dependencies { implementation("org.liquibase:liquibase-core") }'))
    assert 'liquibase' in liqui.lower() or liqui.startswith('#')
    assert 'update' not in liqui.split('#')[0]


def test_workspaces_discover_nested_js_packages_next_to_gradle_modules(build_html, fixture_project):
    root = fixture_project('spring-kts')
    for rel, pkg in {
        'frontend/admin': {'name': '@acme/admin', 'dependencies': {'react': '19'}},
        'frontend/portal': {'name': '@acme/portal', 'dependencies': {'vue': '3'}, 'description': 'Customer portal'},
        'mobile-sdk/ios': {'name': '@acme/sdk-ios', 'dependencies': {'react-native': '0.76'}},
        'tools/cli': {'name': '@acme/cli'},
    }.items():
        os.makedirs(os.path.join(root, rel, 'src'), exist_ok=True)
        json.dump(pkg, open(os.path.join(root, rel, 'package.json'), 'w'))
    open(os.path.join(root, 'frontend', 'admin', 'src', 'main.tsx'), 'w').close()
    open(os.path.join(root, 'frontend', 'admin', '.env'), 'w').write('PORT=5173\n')
    os.makedirs(os.path.join(root, 'frontend', 'admin', 'node_modules', 'left-pad'))
    json.dump({'name': 'left-pad'}, open(os.path.join(root, 'frontend', 'admin', 'node_modules', 'left-pad', 'package.json'), 'w'))

    ws = {w['id']: w for w in build_html._scan_workspaces(root)}
    assert sorted(ws) == ['billing', 'frontend-admin', 'frontend-portal', 'messaging', 'mobile-sdk-ios', 'tools-cli', 'users']
    assert ws['frontend-admin'] == {'id': 'frontend-admin', 'name': '@acme/admin', 'type': 'frontend',
                                    'description': 'Admin UI', 'port': 5173, 'entrypoint': 'frontend/admin/src/main.tsx'}
    assert ws['frontend-portal']['description'] == 'Customer portal'
    assert ws['mobile-sdk-ios']['type'] == 'mobile'
    assert ws['tools-cli']['type'] == 'package'
    assert 'frontend' not in ws                                   # parent dir not reported as a fake port-80 UI


def test_workspaces_express_fixture_unchanged(build_html, fixture_project):
    assert build_html._scan_workspaces(fixture_project('express')) == [
        {'id': 'api', 'name': 'api', 'type': 'backend', 'description': 'Main REST API', 'port': 3000, 'entrypoint': 'src/index.ts'}]


def test_system_endpoints_follow_actuator(build_html, fixture_project):
    data = build_html.init_architecture(fixture_project('spring-kts'))
    assert [e['path'] for e in data['systemEndpoints']] == ['/actuator/health', '/actuator/info', '/actuator/prometheus']
    assert [e['path'] for e in build_html.init_architecture(fixture_project('express'))['systemEndpoints']] == ['/health']
    assert build_html._system_endpoints('spring', {'actuator': False}) == [
        {'method': 'GET', 'path': '/health', 'auth': False, 'description': 'Health check endpoint'}]
    assert [e['path'] for e in build_html._system_endpoints('spring', {'actuator': True, 'contextPath': '/api'})] == [
        '/api/actuator/health', '/api/actuator/info']


# ---------------------------------------------------------------- reviewer findings, round 2

def test_sql_tables_chained_ctes_and_join_fetch(build_html):
    t = build_html._sql_tables
    assert t("WITH eligible AS (SELECT id FROM users WHERE active = true), "
             "priced AS (SELECT e.id, p.amount FROM eligible e JOIN prices p ON p.user_id = e.id) "
             "SELECT * FROM priced WHERE amount > 10") == ['users', 'prices']
    assert t("""WITH a AS (
                    SELECT 1 FROM t1
                ),
                b (x) AS (
                    SELECT x FROM a
                ),
                c AS (SELECT * FROM b JOIN t2 ON 1=1)
                INSERT INTO t3 SELECT * FROM c""") == ['t1', 't2', 't3']
    assert t("SELECT o FROM Order o JOIN FETCH o.orderItems WHERE o.id = :id", jpql=True) == ['Order']
    assert t("SELECT o FROM Order o LEFT JOIN FETCH o.items oi JOIN FETCH oi.product", jpql=True) == ['Order']
    assert t("SELECT * FROM orders o JOIN fetch_log f ON f.order_id = o.id") == ['orders', 'fetch_log']


def test_compose_discovered_in_subfolders_and_merged(build_html, fixture_project, tmp_path):
    root = fixture_project('spring-kts')
    # move the root compose under deployment/ and add a second file with an extra service + an override
    os.makedirs(os.path.join(root, 'deployment'))
    os.rename(os.path.join(root, 'docker-compose.yml'), os.path.join(root, 'deployment', 'docker-compose.yml'))
    with open(os.path.join(root, 'deployment', 'docker-compose.override.yml'), 'w') as f:
        f.write('services:\n  postgres:\n    ports: ["15432:5432"]\n  zipkin:\n    image: openzipkin/zipkin:3\n    ports: ["9411:9411"]\n')
    with open(os.path.join(root, 'docker-compose.test.yml'), 'w') as f:                      # ignored: 'test' variant still a compose file at root
        f.write('services:\n  otel-collector:\n    image: otel/opentelemetry-collector:0.1\n')
    os.makedirs(os.path.join(root, 'node_modules', 'x'))
    with open(os.path.join(root, 'node_modules', 'x', 'docker-compose.yml'), 'w') as f:
        f.write('services:\n  junk:\n    image: junk\n')

    files = [os.path.relpath(f, root) for f in build_html._find_compose_files(root)]
    assert files == ['docker-compose.test.yml', 'deployment/docker-compose.yml', 'deployment/docker-compose.override.yml']

    infra, diagram = build_html._scan_docker(root)
    ids = [s['id'] for s in infra]
    assert 'junk' not in ids
    assert ids[:1] == ['otel-collector']                          # root file first
    assert set(ids) == {'otel-collector', 'api', 'postgres', 'kafka', 'keycloak', 'mailpit', 'nginx', 'zipkin'}
    by = {s['id']: s for s in infra}
    assert by['postgres']['port'] == 5432                         # first definition wins over the override
    assert by['postgres']['source'] == 'deployment/docker-compose.yml'
    assert by['zipkin']['type'] == 'monitoring' and by['zipkin']['source'] == 'deployment/docker-compose.override.yml'
    assert 'deployment/docker-compose.yml' in diagram['description']
    assert build_html._detect_arch_type(root, 'spring') == 'microservice'


def test_messaging_resolves_cross_file_constants(build_html, tmp_path):
    src = tmp_path / 'src' / 'main' / 'java' / 'com' / 'acme'
    (src / 'common').mkdir(parents=True); (src / 'inventory').mkdir()
    (src / 'common' / 'AppConstants.java').write_text('''
        package com.acme.common;
        public final class AppConstants {
            public static final String ORDERS_TOPIC = "orders";
            public static final String PRODUCT_TOPIC = "products";
            public static final String API = "/api";
        }''')
    (src / 'inventory' / 'KafkaListenerConfig.java').write_text('''
        package com.acme.inventory;
        import com.acme.common.AppConstants;
        import static com.acme.common.AppConstants.PRODUCT_TOPIC;
        @Component public class KafkaListenerConfig {
            @KafkaListener(topics = AppConstants.ORDERS_TOPIC, groupId = "inventory") public void onEvent(String e) {}
            @KafkaListener(topics = PRODUCT_TOPIC) public void onProduct(String e) {}
        }''')
    (src / 'inventory' / 'InventoryOrderManageService.java').write_text('''
        package com.acme.inventory;
        import com.acme.common.AppConstants;
        @Service public class InventoryOrderManageService {
            private final KafkaTemplate<String, Object> kafkaTemplate;
            public void reserve(Object o) { kafkaTemplate.send(AppConstants.ORDERS_TOPIC, o); }
        }''')
    (src / 'inventory' / 'InventoryController.java').write_text('''
        package com.acme.inventory;
        import static com.acme.common.AppConstants.*;
        @RestController @RequestMapping(API + "/inventory")
        public class InventoryController { @GetMapping("/{id}") public Object one(@PathVariable Long id) { return null; } }''')
    msg = build_html._scan_messaging_java(str(tmp_path))
    assert [l['topics'] for l in msg['listeners']] == [['orders'], ['products']]
    assert msg['producers'] == [{'broker': 'kafka', 'topic': 'orders', 'handler': 'InventoryOrderManageService.reserve()',
                                 'file': 'src/main/java/com/acme/inventory/InventoryOrderManageService.java'}]
    mods = build_html._scan_java_spring(str(tmp_path), arch_type='monolith')
    ctrl = next(m for m in mods if m['id'] == 'inventory')
    assert ctrl['basePath'] == '/api/inventory' and ctrl['endpoints'][0]['path'] == '/{id}'


def test_skip_overrides_flag(build_html, fixture_project):
    root = fixture_project('express')
    arch_dir = os.path.join(root, 'docs', 'architecture')
    os.makedirs(arch_dir, exist_ok=True)
    with open(os.path.join(arch_dir, 'arch_overrides.py'), 'w') as f:
        f.write('def apply(data, root):\n    raise RuntimeError("hook under development")\n')
    data = build_html.init_architecture(root, skip_overrides=True)
    assert data['meta']['displayName'] == 'Acme Express Api'


def test_no_double_slash_paths_when_base_is_root(build_html, tmp_path):
    src = tmp_path / 'src' / 'main' / 'java'; src.mkdir(parents=True)
    (src / 'FallbackController.java').write_text("""
        @RestController public class FallbackController {
            @GetMapping("/fallback/api/inventory/{id}") public String inv(@PathVariable String id) { return "x"; }
        }""")
    (src / 'HomeController.java').write_text("""
        @Controller @RequestMapping("/") public class HomeController {
            @GetMapping({"", "/"}) public String home() { return "index"; }
            @GetMapping("//login") public String login() { return "login"; }
            @RequestMapping(value = "/api/cart/", method = RequestMethod.GET) public String cart() { return "c"; }
        }""")
    data = build_html.init_architecture(str(tmp_path))
    paths = [p for _, p in endpoints(data)] + [e['path'] for d in data['permissions']['details'] for e in d['endpoints']]
    assert paths and not any('//' in p for p in paths)
    assert sorted(endpoints(data)) == [('GET', '/'), ('GET', '/api/cart'), ('GET', '/fallback/api/inventory/{id}'), ('GET', '/login')]
    out_dir = os.path.join(str(tmp_path), 'docs', 'architecture')
    build_html.generate_html(data, out_dir)
    page = open(os.path.join(out_dir, 'architecture.html'), encoding='utf-8').read()
    import re
    assert not re.search(r'[">]//[a-z{]', page)
