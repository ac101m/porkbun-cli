"""
Safety guards for the live-API test suite.

This suite talks to a real, production Porkbun account, so every
record-modifying request must stay inside a protected subdomain the tests own:
`porkbun_cli_test.<account domain>`. make_safe_api() wraps the mutating api.py
functions so any call that would touch a different domain, or a record outside
that subdomain, fails hard (AssertionError) before a single byte reaches the
network.
"""

import api

# Records touched by the tests are always named under this subdomain.
SAFE_SUBDOMAIN = 'porkbun_cli_test'

# Capture the real implementations up front so the wrappers always delegate to
# the unpatched originals, even if the api module is itself wrapped by an
# active safety gate at the time they run.
_REAL = {
    'retrieve_records': api.retrieve_records,
    'create_record': api.create_record,
    'edit_record': api.edit_record,
    'delete_record': api.delete_record,
}


def safe_record_name(unique):
    """Build a record name guaranteed to live under the protected subdomain."""
    return '{}.{}'.format(SAFE_SUBDOMAIN, unique)


def record_fqdn(name, domain):
    """Fully-qualified name of a record, as the API reports it."""
    return '{}.{}'.format(name, domain)


def _is_safe_name(name):
    bare = name.rstrip('.') if name else ''
    return bare == SAFE_SUBDOMAIN or bare.startswith(SAFE_SUBDOMAIN + '.')


def make_safe_api(account_domain, secret_api_key, api_key, timeout):
    """Return wrapped create/edit/delete confined to the protected subdomain.

    The returned dict mirrors the api.py function names. Each wrapper:
      - refuses any domain other than account_domain;
      - refuses to modify a record whose name is outside SAFE_SUBDOMAIN;
      - for edit/delete, additionally refuses if the *existing* record
        (looked up by id) is not one of ours.
    """

    def check_domain(domain):
        assert domain == account_domain, (
            "Refusing to touch domain '{}': tests may only use '{}'".format(
                domain, account_domain))

    def check_safe_name(name):
        assert name is not None and _is_safe_name(name), (
            "Refusing to touch record '{}': only records under "
            "'{}.<name>' may be modified".format(name, SAFE_SUBDOMAIN))

    def existing_record(domain, id):
        records = _REAL['retrieve_records'](
            domain, secret_api_key, api_key, timeout)['records']
        for record in records:
            # Porkbun returns create/edit ids as ints but retrieve ids as
            # strings; compare stringified so either form matches.
            if str(record['id']) == str(id):
                return record
        return None

    def create_record(domain, secret, key, name, type, content, ttl, prio,
                      request_timeout):
        check_domain(domain)
        check_safe_name(name)
        return _REAL['create_record'](
            domain, secret, key, name, type, content, ttl, prio,
            request_timeout)

    def edit_record(domain, id, secret, key, name, type, content, ttl, prio,
                    request_timeout):
        check_domain(domain)
        existing = existing_record(domain, id)
        if existing is not None:
            check_safe_name(existing['name'])
        check_safe_name(name)
        return _REAL['edit_record'](
            domain, id, secret, key, name, type, content, ttl, prio,
            request_timeout)

    def delete_record(domain, id, secret, key, request_timeout):
        check_domain(domain)
        existing = existing_record(domain, id)
        if existing is None:
            return  # already gone; nothing to delete
        check_safe_name(existing['name'])
        return _REAL['delete_record'](domain, id, secret, key, request_timeout)

    return {
        'create_record': create_record,
        'edit_record': edit_record,
        'delete_record': delete_record,
    }
