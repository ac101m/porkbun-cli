'''
This file implements functions for interacting with the porkbun API.

See here for documentation:
https://porkbun.com/api/json/v3/documentation#Overview
'''

import requests


def get_response(argv):
    try:
        endpoint = argv['endpoint']
        argv.pop('endpoint')
        response = requests.post(endpoint, json=argv)
    except Exception as e:
        print("Oh no! Could not get response from '{}'! {}".format(endpoint, e))
        exit(1)

    if response.status_code != 200:
        print("Oh no! Got {} response from '{}'!".format(response.status_code, endpoint))
        exit(1)

    data = response.json()

    if data['status'] != 'SUCCESS':
        print("Oh no! An API error occurred:\n{} - {}".format(
            data['status'],
            data['message']
        ))
        exit(1)

    return data


def ping(secretapikey, apikey):
    endpoint = 'https://porkbun.com/api/json/v3/ping'
    args = {k: v for k, v in locals().items() if v is not None}
    return get_response(args)


def create_record(domain, secretapikey, apikey, name, type, content, ttl, prio):
    endpoint = 'https://porkbun.com/api/json/v3/dns/create/{}'.format(domain)
    args = {k: v for k, v in locals().items() if v is not None}
    args.pop('domain')
    return get_response(args)


def edit_record(domain, id, secretapikey, apikey, name, type, content, ttl, prio):
    endpoint = 'https://porkbun.com/api/json/v3/dns/edit/{}/{}'.format(domain, id)
    args = {k: v for k, v in locals().items() if v is not None}
    args.pop('domain')
    args.pop('id')
    return get_response(args)


def delete_record(domain, id, secretapikey, apikey):
    endpoint = 'https://porkbun.com/api/json/v3/dns/delete/{}/{}'.format(domain, id)
    args = {k: v for k, v in locals().items() if v is not None}
    args.pop('domain')
    args.pop('id')
    return get_response(args)


def retrieve_records(domain, secretapikey, apikey):
    endpoint = 'https://porkbun.com/api/json/v3/dns/retrieve/{}'.format(domain)
    args = {k: v for k, v in locals().items() if v is not None}
    args.pop('domain')
    return get_response(args)
