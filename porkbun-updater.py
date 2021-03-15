#!/usr/bin/env python3

'''
[porkbun dynamic DNS updater]
Dynamic IP got you down? Here's a tool for updating your porkbun domains!

Usage:
  porkbun-updater (-h | --help)
  porkbun-updater ping [options]
  porkbun-updater record list <domain>
  porkbun-updater record create <domain> [--name=<name>] [--type=<type>] [--ttl=<ttl>] [--content=<ip>] [--priority=<prio>] [options]
  porkbun-updater record edit <domain> <id> [--name=<name>] [--type=<type>] [--ttl=<ttl>] [--content=<ip>] [--priority=<prio>] [options]
  porkbun-updater record update <domain> <id> [--content=<ip>] [options]
  porkbun-updater record delete <domain> <id> [options]

Options:
  -h --help                 Display this help message.
  --delay=<seconds>         How frequently should the updater check for IP address changes in seconds. When specified,
                            the update command will run periodically rather than just once.
  --apikey=<path>           Path to api key file. [default: api-key]
  --secretapikey=<path>     Path to secret api key file. [default: secret-api-key]
'''

import docopt
import requests
import time

import api



def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[:-len(suffix)]
    return s


def load_file(path):
    try:
        return open(path, 'r').read().strip()
    except Exception as e:
        print("Oh no! Could not open keyfile! {}".format(e))
        exit(1)


def get_external_ip():
    try:
        return requests.get('https://api.ipify.org').text.strip()
    except Exception as e:
        print("Oh no! Could not get external IP! {}".format(e))
        exit(1)


def ping(secretapikey, apikey):
    print('Pinging porkbun...')
    response = api.ping(secretapikey, apikey)
    print('Porkbun says {}!'.format(response['status']))


def record_list(secretapikey, apikey, domain):
    response = api.retrieve_records(domain, secretapikey, apikey)
    print('Showing all records for {}'.format(domain))
    for record in response['records']:
        print('{}:'.format(record['name']))
        print(' - id: {}'.format(record['id']))
        print(' - type: {}'.format(record['type']))
        print(' - content: {}'.format(record['content']))
        print(' - ttl: {}'.format(record['ttl']))
        print(' - prio: {}'.format(record['prio']))


def record_create(secretapikey, apikey, domain, id, args):
    name = args['--name'] if args['--name'] is not None else ''
    type = args['--type'] if args['--type'] is not None else 'A'
    ttl = args['--ttl'] if args['--ttl'] is not None else '300'
    content = args['--content'] if args['--content'] is not None else get_external_ip()
    prio = args['--priority'] if args['--priority'] is not None else '0'
    print('Creating new record {}.{}'.format(name, domain))
    print(' - type: {}'.format(type))
    print(' - content: {}'.format(content))
    print(' - ttl: {}'.format(ttl))
    print(' - prio: {}'.format(prio))
    response = api.create_record(domain, secretapikey, apikey, name, type, content, ttl, prio)
    print('Record created successfully! id: {}'.format(response['id']))


def get_record(secretapikey, apikey, domain, id):
    record = None
    for r in api.retrieve_records(domain, secretapikey, apikey)['records']:
        if r['id'] == id:
            record = r
    if record is None:
        print("No record with id '{}' exists!".format(id))
        exit(1)
    return record


def record_edit(secretapikey, apikey, domain, id, args):
    print('Editing record {}/{}'.format(domain, id))
    record = get_record(secretapikey, apikey, domain, id)
    name = args['--name'] if args['--name'] is not None else rchop(record['name'], domain)
    type = args['--type'] if args['--type'] is not None else record['type']
    ttl = args['--ttl'] if args['--ttl'] is not None else record['ttl']
    content = args['--content'] if args['--content'] is not None else record['content']
    prio = args['--priority'] if args['--priority'] is not None else record['prio']
    api.edit_record(domain, id, secretapikey, apikey, name, type, content, ttl, prio)
    print('Record updated!')
    print(' - type: {}'.format(type))
    print(' - content: {}'.format(content))
    print(' - ttl: {}'.format(ttl))
    print(' - prio: {}'.format(prio))


def record_update(secretapikey, apikey, domain, id, content):
    print("Updating record {}/{}".format(domain, id))
    record = get_record(secretapikey, apikey, domain, id)
    name = rchop(record['name'], domain).strip('.')
    type = record['type']
    ttl = record['ttl']
    prio = record['prio']
    if record['content'] == content:
        print('Content unchanged, no update is neccessary!')
    else:
        api.edit_record(domain, id, secretapikey, apikey, name, type, content, ttl, prio)
        print('Record updated successfully! New content: {}'.format(content))


def record_update_continuous(secretapikey, apikey, domain, id, delay):
    record_ip = get_record(secretapikey, apikey, domain, id)['content']
    while True:
        try:
            current_ip = get_external_ip()
            if record_ip != current_ip:
                print('External IP address does not match record!')
                record_update(secretapikey, apikey, domain, id, current_ip)
                record_ip = current_ip
        except Exception as e:
            print("Error occurred during update: {}".format(e))
        time.sleep(delay)


def record_delete(secretapikey, apikey, domain, id):
    print('Deleting record {}/{}'.format(domain, id))
    api.delete_record(domain, id, secretapikey, apikey)
    print('Record deleted.')


def record(secretapikey, apikey, args):
    id = args['<id>']
    domain = args['<domain>']
    if args['list']:
        record_list(secretapikey, apikey, domain)
    elif args['create']:
        record_create(secretapikey, apikey, domain, id, args)
    elif args['edit']:
        record_edit(secretapikey, apikey, domain, id, args)
    elif args['update']:
        if args['--delay'] is None:
            content = args['--content'] if args['--content'] is not None else get_external_ip()
            record_update(secretapikey, apikey, domain, id, content)
        else:
            try:
                delay = int(args['--delay'])
            except ValueError as e:
                print("Oh no! '{}' is not an integer!".format(args['--delay']))
                exit(1)
            if delay <= 0:
                print('Oh no! Check frequency must be greater than or equal to zero!')
            else:
                record_update_continuous(secretapikey, apikey, domain, id, delay)
    elif args['delete']:
        record_delete(secretapikey, apikey, domain, id)


def run(args):
    secretapikey = load_file(args['--secretapikey'])
    apikey = load_file(args['--apikey'])
    if args['ping']:
        ping(secretapikey, apikey)
    elif args['record']:
        record(secretapikey, apikey, args)


if __name__ == '__main__':
    run(docopt.docopt(__doc__))
