"""
Shared test configuration.

The tests exercise the real Porkbun API, so they need the developer to
provide two API keys and a domain to operate on. Those live in plain
files at the project root (gitignored), mirroring how porkbun-cli itself
reads its keyfiles:

    api-key         - Porkbun API key
    secret-api-key  - Porkbun secret API key
    test-domain     - a domain the keys are authorized to manipulate

If any are missing or empty, the whole test run is aborted up front with
a message telling the developer what to create.
"""

import importlib.util
import pathlib
import sys
import time

import pytest

import api

# Make the sibling helper modules (safety.py) importable from this conftest,
# independent of pytest's sys.path handling.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import safety  # noqa: E402

# tests/ sits directly under the project root.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Request timeout shared by the tests when talking to the API.
TIMEOUT = 10

# Pause inserted before every API request, out of consideration for Porkbun's
# servers (the live API has rate limits, and tests make many requests).
REQUEST_DELAY = 1.0

REQUIRED_FILES = {
    'api-key': 'your Porkbun API key',
    'secret-api-key': 'your Porkbun secret API key',
    'test-domain': 'the domain the keys are authorized to manipulate (e.g. test.example.com)',
}


def _read_config():
    """Load the required config files, aborting with a helpful error if any are missing."""
    provided = {}
    missing = []
    for name, purpose in REQUIRED_FILES.items():
        path = PROJECT_ROOT / name
        if not path.is_file():
            missing.append(path)
            continue
        value = path.read_text().strip()
        if not value:
            missing.append(path)
            continue
        provided[name] = value

    if missing:
        details = '\n'.join(
            "  - '{}': {} (e.g. `echo '...' > {}`)".format(path.relative_to(PROJECT_ROOT), REQUIRED_FILES[path.name], path.name)
            for path in missing
        )
        # Abort before any collection or tests run, with a clean no-traceback exit.
        pytest.exit(
            "\nCannot run the porkbun-cli tests: the following developer-provided\n"
            "configuration is missing or empty:\n"
            "{}\n\n"
            "These files are not committed to version control and must be created by\n"
            "whoever runs the tests.\n".format(details),
            returncode=1,
        )

    return provided


def pytest_configure(config):
    """Run the config check at session start so a missing setup aborts the run cleanly."""
    global _CONFIG
    _CONFIG = _read_config()
    # Be kind to Porkbun: pause REQUEST_DELAY seconds before every API request
    # in this session. Every api.py function funnels through get_response, so
    # this covers direct calls, the safety-gate's record lookups, CLI-driven
    # requests, and the end-of-run sweep alike. Patching here (rather than a
    # fixture) also keeps the delay active through session teardown.
    original_get_response = api.get_response

    def _delayed_get_response(argv, timeout):
        time.sleep(REQUEST_DELAY)
        return original_get_response(argv, timeout)

    api.get_response = _delayed_get_response


_CONFIG = None


@pytest.fixture(scope='session')
def api_key():
    return _CONFIG['api-key']


@pytest.fixture(scope='session')
def secret_api_key():
    return _CONFIG['secret-api-key']


@pytest.fixture(scope='session')
def test_domain():
    return _CONFIG['test-domain']


@pytest.fixture(autouse=True)
def record_safety(monkeypatch):
    """Wrap the mutating api.py functions so every record-modifying request in
    the suite is confined to the protected 'porkbun_cli_test.<test-domain>'
    subdomain (see safety.py). Refusals raise AssertionError before any
    request is sent."""
    gate = safety.make_safe_api(
        _CONFIG['test-domain'], _CONFIG['secret-api-key'], _CONFIG['api-key'], TIMEOUT)
    for name in ('create_record', 'edit_record', 'delete_record'):
        monkeypatch.setattr(api, name, gate[name])


@pytest.fixture(scope='session', autouse=True)
def _sweep_test_records():
    """Final safety net: after the whole run, remove any records still present
    under the protected 'porkbun_cli_test.' subdomain.

    Every test removes its own records on teardown; this catches anything a
    failed or aborted test left behind, so a run can never pollute the live
    zone with test data. Runs with the unwrapped api functions (the per-test
    safety gate has been torn down by then)."""
    yield
    domain = _CONFIG['test-domain']
    secret = _CONFIG['secret-api-key']
    key = _CONFIG['api-key']
    try:
        records = api.retrieve_records(domain, secret, key, TIMEOUT)['records']
    except api.PorkbunAPIError as e:
        print('sweep: could not list records for {}: {}'.format(domain, e))
        return
    strays = [r for r in records if r['name'].startswith(safety.SAFE_SUBDOMAIN + '.')]
    for record in strays:
        try:
            api.delete_record(domain, record['id'], secret, key, TIMEOUT)
        except api.PorkbunAPIError as e:
            print('sweep: failed to remove {}: {}'.format(record['name'], e))
        else:
            print('sweep: removed leftover test record {}'.format(record['name']))
    if strays:
        print('sweep: cleared {} leftover test record(s)'.format(len(strays)))


@pytest.fixture(scope='session')
def cli():
    """Load src/porkbun-cli.py as a module.

    The filename is hyphenated, so it can't be imported by name; load it by
    path instead (its `import api` resolves via the pythonpath config).
    """
    path = PROJECT_ROOT / 'src' / 'porkbun-cli.py'
    spec = importlib.util.spec_from_file_location('porkbun_cli', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
