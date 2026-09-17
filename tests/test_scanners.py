"""Scanner accuracy tests against the small fixture projects in tests/fixtures/.

Express and FastAPI assertions pin the existing behaviour; the Spring fixture
exercises the Gradle Kotlin-DSL / multi-path / @Query / docker-compose fixes.
"""
import json
import os

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
    json.loads(html.split('id="swaggerOpenApiJsonSrc">', 1)[1].split('</code>', 1)[0]
               .replace('&quot;', '"').replace('&#x27;', "'").replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&'))


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
