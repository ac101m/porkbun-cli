"""
This file implements functions for interacting with the porkbun API.

See here for documentation:
https://porkbun.com/api/json/v3/documentation#Overview
"""

import requests


requests.packages.urllib3.util.connection.HAS_IPV6 = False


BASE_URL = 'https://api.porkbun.com'


class PorkbunAPIError(Exception):
    pass


def format_url(path):
    return '{}/{}'.format(BASE_URL, path)


def get_response(argv, timeout):
    try:
        endpoint = argv['endpoint']
        argv.pop('endpoint')
        response = requests.post(endpoint, json=argv, timeout=timeout)
    except Exception as e:
        raise PorkbunAPIError("Oh no! Could not get response from '{}'! {}".format(endpoint, e))

    if response.status_code != 200:
        raise PorkbunAPIError("Oh no! Got {} response from '{}'!".format(response.status_code, endpoint))

    data = response.json()

    if data['status'] != 'SUCCESS':
        raise PorkbunAPIError("Oh no! An API error occurred:\n{} - {}".format(data['status'], data['message']))

    return data


def ping(secret_api_key, api_key, timeout):
    endpoint = format_url('api/json/v3/ping')
    args = {'endpoint': endpoint, 'secretapikey': secret_api_key, 'apikey': api_key}
    return get_response(args, timeout)


def create_record(domain, secret_api_key, api_key, name, type, content, ttl, prio, timeout):
    endpoint = format_url('api/json/v3/dns/create/{}'.format(domain))
    args = {'endpoint': endpoint, 'secretapikey': secret_api_key, 'apikey': api_key}
    if name is not None:
        args['name'] = name
    if type is not None:
        args['type'] = type
    if content is not None:
        args['content'] = content
    if ttl is not None:
        args['ttl'] = ttl
    if prio is not None:
        args['prio'] = prio
    return get_response(args, timeout)


def edit_record(domain, id, secret_api_key, api_key, name, type, content, ttl, prio, timeout):
    endpoint = format_url('api/json/v3/dns/edit/{}/{}'.format(domain, id))
    args = {'endpoint': endpoint, 'secretapikey': secret_api_key, 'apikey': api_key}
    if name is not None:
        args['name'] = name
    if type is not None:
        args['type'] = type
    if content is not None:
        args['content'] = content
    if ttl is not None:
        args['ttl'] = ttl
    if prio is not None:
        args['prio'] = prio
    return get_response(args, timeout)


def delete_record(domain, id, secret_api_key, api_key, timeout):
    endpoint = format_url('api/json/v3/dns/delete/{}/{}'.format(domain, id))
    args = {'endpoint': endpoint, 'secretapikey': secret_api_key, 'apikey': api_key}
    return get_response(args, timeout)


def retrieve_records(domain, secret_api_key, api_key, timeout):
    endpoint = format_url('api/json/v3/dns/retrieve/{}'.format(domain))
    args = {'endpoint': endpoint, 'secretapikey': secret_api_key, 'apikey': api_key}
    return get_response(args, timeout)
