import importlib.util
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, 'tests', 'fixtures')
SCRIPT = os.path.join(ROOT, 'templates', 'build_html.py')


@pytest.fixture(scope='session')
def build_html():
    """Import templates/build_html.py as a module (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location('build_html', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['build_html'] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def fixture_project(tmp_path):
    """Copy a fixture project into a temp dir so the scan never dirties tests/fixtures."""
    def _copy(name):
        dst = tmp_path / name
        shutil.copytree(os.path.join(FIXTURES, name), dst)
        return str(dst)
    return _copy


def endpoints(data):
    """Flatten (METHOD, full_path) pairs from a scanned manifest."""
    out = []
    for mod in data['modules']:
        bp = mod['basePath']
        for ep in mod['endpoints']:
            full = (bp + ('' if ep['path'] == '/' else ep['path'])).replace('//', '/')
            out.append((ep['method'], full))
    return out


def endpoint_index(data):
    """(METHOD, full_path) -> endpoint dict, for asserting on auth/permission fields."""
    idx = {}
    for mod in data['modules']:
        bp = mod['basePath']
        for ep in mod['endpoints']:
            full = (bp + ('' if ep['path'] == '/' else ep['path'])).replace('//', '/')
            idx[(ep['method'], full)] = ep
    return idx
