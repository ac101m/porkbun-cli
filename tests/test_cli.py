"""
End-to-end tests for the CLI functionality (src/porkbun-cli.py).

Tests drive the tool through its real entrypoint path - docopt.parse() on the
module's own usage string, then run() - against the live Porkbun API, using
the developer-provided keys and test domain.

Safety: every record the tests create lives under the protected
`porkbun_cli_test.` subdomain (see safety.py), has a unique name so runs never
collide, and is deleted on teardown regardless of whether the test passes or
fails. All record-modifying API calls are additionally confined by an autouse
gate in conftest.py.
"""

import ipaddress
import time
import uuid
from pathlib import Path

import pytest

import api
import safety

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_KEY_PATH = PROJECT_ROOT / 'api-key'
SECRET_KEY_PATH = PROJECT_ROOT / 'secret-api-key'

TIMEOUT = 10

# IPv4 content used for the records this suite creates and manipulates.
# 192.0.2.0/24 and 203.0.113.0/24 are TEST-NET ranges reserved for docs.
TEST_IP = '192.0.2.1'
OTHER_IP = '192.0.2.2'


def run_cli(cli, *argv):
    """Parse argv with the tool's own docopt usage, then execute it.

    The key paths are always passed explicitly so the tests don't depend on
    the process working directory being the project root.
    """
    import docopt
    full_argv = [
        '--apikey={}'.format(API_KEY_PATH),
        '--secretapikey={}'.format(SECRET_KEY_PATH),
    ] + list(argv)
    args = docopt.docopt(cli.__doc__, argv=full_argv)
    cli.run(args)


def retrieve(domain, secret_api_key, api_key):
    return api.retrieve_records(domain, secret_api_key, api_key, TIMEOUT)['records']


def record_by_fqdn(records, fqdn):
    target = fqdn.rstrip('.')
    for record in records:
        if record['name'].rstrip('.') == target:
            return record
    return None


def record_by_id(records, id):
    for record in records:
        if record['id'] == id:
            return record
    return None


def wait_until(condition, timeout=30, interval=1.0):
    """Poll condition() until it's truthy; return the last value it produced."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = condition()
        if value:
            return value
        time.sleep(interval)
    return condition()


def unique_name():
    # Names are always scoped under the protected test subdomain.
    return safety.safe_record_name('pytest-{}'.format(uuid.uuid4().hex))


def delete_record_if_present(domain, secret_api_key, api_key, fqdn):
    """Best-effort cleanup of a record located by its fully-qualified name."""
    try:
        record = record_by_fqdn(retrieve(domain, secret_api_key, api_key), fqdn)
    except api.PorkbunAPIError:
        return
    if record is not None:
        try:
            api.delete_record(domain, record['id'], secret_api_key, api_key, TIMEOUT)
        except api.PorkbunAPIError:
            pass


@pytest.fixture
def managed_record(api_key, secret_api_key, test_domain):
    """Create a unique A record for the test; guarantee its deletion afterwards."""
    name = unique_name()
    fqdn = safety.record_fqdn(name, test_domain)
    response = api.create_record(
        test_domain, secret_api_key, api_key, name, 'A', TEST_IP, '300', '0', TIMEOUT)
    # The create endpoint returns id as an int, but retrieve reports it as a
    # string; the CLI always sees ids as strings, so tests use the string form.
    record_id = str(response['id'])

    created = wait_until(
        lambda: record_by_fqdn(retrieve(test_domain, secret_api_key, api_key), fqdn))
    assert created is not None, \
        'created record {} never became visible through the API'.format(fqdn)

    yield {'name': name, 'fqdn': fqdn, 'id': record_id, 'domain': test_domain}

    # Teardown: remove the record even if the test failed part-way.
    try:
        api.delete_record(test_domain, record_id, secret_api_key, api_key, TIMEOUT)
    except api.PorkbunAPIError:
        pass  # Record may already have been deleted by the test itself.


def test_show_ip_reports_external_address(cli, capsys):
    run_cli(cli, 'show_ip')
    out = capsys.readouterr().out.strip()
    assert out, 'show_ip printed nothing'
    ipaddress.ip_address(out)  # raises ValueError if the output isn't an IP


def test_ping_reports_success(cli, capsys):
    run_cli(cli, 'ping')
    out = capsys.readouterr().out
    assert 'SUCCESS' in out


def test_record_list_shows_managed_record(cli, capsys, managed_record):
    run_cli(cli, 'record', 'list', managed_record['domain'])
    out = capsys.readouterr().out
    assert managed_record['fqdn'] in out
    assert managed_record['id'] in out


def test_record_create_makes_record(cli, api_key, secret_api_key, test_domain):
    name = unique_name()
    fqdn = safety.record_fqdn(name, test_domain)
    try:
        run_cli(cli, 'record', 'create', test_domain,
                '--name', name, '--type', 'A', '--content', TEST_IP)
        record = wait_until(
            lambda: record_by_fqdn(retrieve(test_domain, secret_api_key, api_key), fqdn))
        assert record is not None, 'created record never became visible'
        assert record['type'] == 'A'
        assert record['content'] == TEST_IP
    finally:
        delete_record_if_present(test_domain, secret_api_key, api_key, fqdn)


def test_record_edit_updates_content(cli, api_key, secret_api_key, managed_record):
    # No --name is passed: the tool derives it from the existing record, which
    # is the path users hit when they only want to change content.
    run_cli(cli, 'record', 'edit', managed_record['domain'], managed_record['id'],
            '--content', OTHER_IP)
    record = wait_until(lambda: record_by_id(
        retrieve(managed_record['domain'], secret_api_key, api_key), managed_record['id']))
    assert record is not None
    assert record['content'] == OTHER_IP


def test_record_update_changes_content(cli, api_key, secret_api_key, managed_record):
    run_cli(cli, 'record', 'update', managed_record['domain'], managed_record['id'],
            '--content', OTHER_IP)
    record = wait_until(lambda: record_by_id(
        retrieve(managed_record['domain'], secret_api_key, api_key), managed_record['id']))
    assert record is not None
    assert record['content'] == OTHER_IP


def test_record_update_noop_when_content_unchanged(cli, capsys, api_key, secret_api_key,
                                                   managed_record):
    # Same content as the fixture created the record with.
    run_cli(cli, 'record', 'update', managed_record['domain'], managed_record['id'],
            '--content', TEST_IP)
    out = capsys.readouterr().out
    assert 'Content unchanged, no update is neccessary!' in out
    record = record_by_id(
        retrieve(managed_record['domain'], secret_api_key, api_key), managed_record['id'])
    assert record is not None
    assert record['content'] == TEST_IP


def test_record_delete_removes_record(cli, api_key, secret_api_key, managed_record):
    run_cli(cli, 'record', 'delete', managed_record['domain'], managed_record['id'])
    gone = wait_until(lambda: record_by_id(
        retrieve(managed_record['domain'], secret_api_key, api_key), managed_record['id']) is None)
    assert gone, 'record still present after delete'


def test_record_update_continuous_updates_only_on_ip_change(cli, monkeypatch):
    """The updater should update on the first poll, then only when the IP changes.

    A deterministic unit test of the loop: the API calls are stubbed, so no
    live requests are made (the real API is exercised by the other tests).
    """
    calls = []
    polls = {'count': 0}

    def fake_get_external_ip(secret_api_key, api_key, timeout):
        polls['count'] += 1
        if polls['count'] == 3:
            raise SystemExit  # break out of the infinite loop after two polls
        return '203.0.113.1'

    def fake_record_update(secret_api_key, api_key, domain, id, content, timeout):
        calls.append(content)

    class _FakeTime:
        @staticmethod
        def sleep(seconds):
            pass

    class _FakeSignal:
        SIGINT = 2

        @staticmethod
        def signal(signum, handler):
            pass

    monkeypatch.setattr(cli, 'get_external_ip', fake_get_external_ip)
    monkeypatch.setattr(cli, 'record_update', fake_record_update)
    monkeypatch.setattr(cli, 'time', _FakeTime)
    monkeypatch.setattr(cli, 'signal', _FakeSignal)
    try:
        with pytest.raises(SystemExit):
            cli.record_update_continuous('secret', 'key', 'test.hsh.ac', '12345', 1, TIMEOUT)
    finally:
        cli.interactive = True

    # Poll 1: last_ip starts as None, so one update happens.
    # Poll 2: IP unchanged, so no update is made.
    assert calls == ['203.0.113.1']
