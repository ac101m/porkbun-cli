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

import pathlib

import pytest

# tests/ sits directly under the project root.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

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
