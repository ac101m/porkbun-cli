"""
Tests for the api.py wire layer against the live Porkbun API.

These use the developer-provided keys and test domain. The record CRUD
endpoints (create/edit/delete) are exercised end-to-end through the CLI in
test_cli.py; here we cover ping, listing, and the API error paths.
"""

import ipaddress
import uuid

import pytest

import api

TIMEOUT = 10


def test_ping_succeeds(api_key, secret_api_key):
    response = api.ping(secret_api_key, api_key, TIMEOUT)
    assert response['status'] == 'SUCCESS'


def test_ping_reports_external_ip(api_key, secret_api_key):
    response = api.ping(secret_api_key, api_key, TIMEOUT)
    # yourIp is the caller's current public address; it must parse as an IP.
    ipaddress.ip_address(response['yourIp'])


def test_bad_credentials_raise(api_key, secret_api_key):
    with pytest.raises(api.PorkbunAPIError):
        api.ping('definitely-not-a-valid-secret', 'definitely-not-a-valid-key', TIMEOUT)


def test_retrieve_returns_record_shape(test_domain, api_key, secret_api_key):
    response = api.retrieve_records(test_domain, secret_api_key, api_key, TIMEOUT)
    assert response['status'] == 'SUCCESS'
    records = response['records']
    assert isinstance(records, list)
    # A zone under Porkbun always carries at least its NS records.
    assert len(records) > 0
    for record in records:
        for field in ('id', 'name', 'type', 'content', 'ttl', 'prio'):
            assert field in record


def test_unknown_domain_raises(api_key, secret_api_key):
    domain = 'definitely-not-a-real-{}.com'.format(uuid.uuid4().hex)
    with pytest.raises(api.PorkbunAPIError):
        api.retrieve_records(domain, secret_api_key, api_key, TIMEOUT)
