'''
This file implements functions for interacting with the porkbun API.

See here for documentation:
https://porkbun.com/api/json/v3/documentation#Overview
'''

import requests


BASE_URL = 'https://api.porkbun.com'


class PorkbunAPIError(Exception):
    pass


def format_url(path):
    return '{}/{}'.format(BASE_URL, path)


def get_response(argv):
    try:
        endpoint = argv['endpoint']
        argv.pop('endpoint')
        response = requests.post(endpoint, json=argv)
    except Exception as e:
        raise PorkbunAPIError("Oh no! Could not get response from '{}'! {}".format(endpoint, e))

    if response.status_code != 200:
        raise PorkbunAPIError("Oh no! Got {} response from '{}'!".format(response.status_code, endpoint))

    data = response.json()

    if data['status'] != 'SUCCESS':
        raise PorkbunAPIError("Oh no! An API error occurred:\n{} - {}".format(data['status'], data['message']))

    return data


def ping(secretapikey, apikey):
    endpoint = format_url('api/json/v3/ping')
    args = {k: v for k, v in locals().items() if v is not None}
    return get_response(args)


def create_record(domain, secretapikey, apikey, name, type, content, ttl, prio):
    endpoint = format_url('api/json/v3/dns/create/{}'.format(domain))
    args = {k: v for k, v in locals().items() if v is not None}
    args.pop('domain')
    return get_response(args)


def edit_record(domain, id, secretapikey, apikey, name, type, content, ttl, prio):
    endpoint = format_url('api/json/v3/dns/edit/{}/{}'.format(domain, id))
    args = {k: v for k, v in locals().items() if v is not None}
    args.pop('domain')
    args.pop('id')
    return get_response(args)


def delete_record(domain, id, secretapikey, apikey):
    endpoint = format_url('api/json/v3/dns/delete/{}/{}'.format(domain, id))
    args = {k: v for k, v in locals().items() if v is not None}
    args.pop('domain')
    args.pop('id')
    return get_response(args)


def retrieve_records(domain, secretapikey, apikey):
    endpoint = format_url('api/json/v3/dns/retrieve/{}'.format(domain))
    args = {k: v for k, v in locals().items() if v is not None}
    args.pop('domain')
    return get_response(args)
