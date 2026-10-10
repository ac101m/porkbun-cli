"""
Tests for the safety guards that confine the live-API suite to the protected
test subdomain (tests/safety.py). These make no network requests: every case
exercises a refusal path, and the wrappers refuse before any HTTP call.
"""

import pytest

import safety


def test_safe_record_name_is_under_protected_subdomain():
    name = safety.safe_record_name('abc123')
    assert name == 'porkbun_cli_test.abc123'
    assert safety.record_fqdn(name, 'ac101m.com') == \
        'porkbun_cli_test.abc123.ac101m.com'


@pytest.mark.parametrize('candidate,expected', [
    ('porkbun_cli_test.host', True),
    ('porkbun_cli_test.host.', True),   # trailing dot from rchop-style code
    ('porkbun_cli_test', True),
    ('host', False),
    ('other.host.ac101m.com', False),   # fully-qualified but not ours
    ('', False),
    (None, False),
])
def test_is_safe_name(candidate, expected):
    assert safety._is_safe_name(candidate) is expected


@pytest.mark.parametrize('bad_name', [
    'www',                        # plain hostname, outside our subdomain
    'other.zone.ac101m.com',      # fully-qualified, still outside
    '',                           # empty name (zone apex)
    None,                         # no name at all
])
def test_gate_rejects_unprotected_name(bad_name):
    # A gate bound to a fake domain with fake credentials: the refusal must
    # happen before any request is attempted, so no network is involved.
    gate = safety.make_safe_api('fake.test', 'nope', 'nope', 10)
    with pytest.raises(AssertionError):
        gate['create_record']('fake.test', 'nope', 'nope', bad_name,
                              'A', '192.0.2.1', '300', '0', 10)


@pytest.mark.parametrize('bad_domain', ['other.com', 'ac101m.com'])
def test_gate_rejects_wrong_domain(bad_domain):
    # Even ac101m.com is rejected here because this gate is bound to
    # 'fake.test' - proving the check depends on the gate, not the real config.
    gate = safety.make_safe_api('fake.test', 'nope', 'nope', 10)
    with pytest.raises(AssertionError):
        gate['create_record'](bad_domain, 'nope', 'nope', 'porkbun_cli_test.x',
                              'A', '192.0.2.1', '300', '0', 10)


def test_gate_edit_rejects_wrong_domain_before_lookup():
    # Domain check runs first, so no record lookup (no network) is attempted.
    gate = safety.make_safe_api('fake.test', 'nope', 'nope', 10)
    with pytest.raises(AssertionError):
        gate['edit_record']('other.test', '123', 'nope', 'nope',
                            'porkbun_cli_test.x', 'A', '1.2.3.4', '300', '0', 10)


def test_gate_delete_rejects_wrong_domain():
    gate = safety.make_safe_api('fake.test', 'nope', 'nope', 10)
    with pytest.raises(AssertionError):
        gate['delete_record']('other.test', '123', 'nope', 'nope', 10)
