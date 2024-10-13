#!/usr/bin/env python3

'''
[porkbun-cli]
A command line tool for managing and updating your porkbun domains!

Usage:
  porkbun-cli (-h | --help)
  porkbun-cli show_ip
  porkbun-cli ping [options]
  porkbun-cli record list <domain>
  porkbun-cli record create <domain> [--name=<name>] [--type=<type>] [--ttl=<ttl>] [--content=<ip>] [--priority=<prio>] [options]
  porkbun-cli record edit <domain> <id> [--name=<name>] [--type=<type>] [--ttl=<ttl>] [--content=<ip>] [--priority=<prio>] [options]
  porkbun-cli record update <domain> <id> [--content=<ip>] [options]
  porkbun-cli record delete <domain> <id> [options]

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
import signal
from datetime import datetime

import api


def now():
    return datetime.now().strftime('%b %d %H:%M:%S')


# This is set to false if running the continuous updater
interactive = True


def log(message):
    if interactive:
        print(message)
    else:
        print('[{}] - {}'.format(now(), message))


def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[:-len(suffix)]
    return s


def load_file(path):
    try:
        return open(path, 'r').read().strip()
    except Exception as e:
        log("Oh no! Could not open keyfile! {}".format(e))
        exit(1)


def get_external_ip(secretapikey, apikey):
    response = api.ping(secretapikey, apikey)
    return response['yourIp']


def ping(secretapikey, apikey):
    log('Pinging porkbun...')
    response = api.ping(secretapikey, apikey)
    log('Porkbun says {}!'.format(response['status']))


def record_list(secretapikey, apikey, domain):
    response = api.retrieve_records(domain, secretapikey, apikey)
    log('Showing all records for {}'.format(domain))
    for record in response['records']:
        log('{}:'.format(record['name']))
        log(' - id: {}'.format(record['id']))
        log(' - type: {}'.format(record['type']))
        log(' - content: {}'.format(record['content']))
        log(' - ttl: {}'.format(record['ttl']))
        log(' - prio: {}'.format(record['prio']))


def record_create(secretapikey, apikey, domain, id, args):
    name = args['--name'] if args['--name'] is not None else ''
    type = args['--type'] if args['--type'] is not None else 'A'
    ttl = args['--ttl'] if args['--ttl'] is not None else '300'
    content = args['--content'] if args['--content'] is not None else get_external_ip()
    prio = args['--priority'] if args['--priority'] is not None else '0'
    log('Creating new record {}.{}'.format(name, domain))
    log(' - type: {}'.format(type))
    log(' - content: {}'.format(content))
    log(' - ttl: {}'.format(ttl))
    log(' - prio: {}'.format(prio))
    response = api.create_record(domain, secretapikey, apikey, name, type, content, ttl, prio)
    log('Record created successfully! id: {}'.format(response['id']))


def get_record(secretapikey, apikey, domain, id):
    record = None
    for r in api.retrieve_records(domain, secretapikey, apikey)['records']:
        if r['id'] == id:
            record = r
    if record is None:
        log("No record with id '{}' exists!".format(id))
        exit(1)
    return record


def record_edit(secretapikey, apikey, domain, id, args):
    log('Editing record {}/{}'.format(domain, id))
    record = get_record(secretapikey, apikey, domain, id)
    name = args['--name'] if args['--name'] is not None else rchop(record['name'], domain)
    type = args['--type'] if args['--type'] is not None else record['type']
    ttl = args['--ttl'] if args['--ttl'] is not None else record['ttl']
    content = args['--content'] if args['--content'] is not None else record['content']
    prio = args['--priority'] if args['--priority'] is not None else record['prio']
    api.edit_record(domain, id, secretapikey, apikey, name, type, content, ttl, prio)
    log('Record updated!')
    log(' - type: {}'.format(type))
    log(' - content: {}'.format(content))
    log(' - ttl: {}'.format(ttl))
    log(' - prio: {}'.format(prio))


def record_update(secretapikey, apikey, domain, id, content):
    log("Updating record {}/{}".format(domain, id))
    record = get_record(secretapikey, apikey, domain, id)
    name = rchop(record['name'], domain).strip('.')
    type = record['type']
    ttl = record['ttl']
    prio = record['prio']
    if record['content'] == content:
        log('Content unchanged, no update is neccessary!')
    else:
        api.edit_record(domain, id, secretapikey, apikey, name, type, content, ttl, prio)
        log('Record updated successfully! New content: {}'.format(content))


def record_update_continuous(secretapikey, apikey, domain, id, delay):
    global interactive
    interactive = False
    log('Updater active! delay: {}s'.format(delay))
    def sigint_handler(signal, frame):
        log('Received SIGINT, stopping updater.')
        exit(0)
    signal.signal(signal.SIGINT, sigint_handler)
    last_ip = None
    while True:
        try:
            current_ip = get_external_ip(secretapikey, apikey)
            if current_ip != last_ip:
                log('Updating record to {}'.format(current_ip))
                record_update(secretapikey, apikey, domain, id, current_ip)
            last_ip = current_ip
        except Exception as e:
            log("Error occurred during update: {}".format(e))
        finally:
            time.sleep(delay)


def record_delete(secretapikey, apikey, domain, id):
    log('Deleting record {}/{}'.format(domain, id))
    api.delete_record(domain, id, secretapikey, apikey)
    log('Record deleted.')


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
                log("Oh no! '{}' is not an integer!".format(args['--delay']))
                exit(1)
            if delay <= 0:
                log('Oh no! Check frequency must be greater than or equal to zero!')
            else:
                record_update_continuous(secretapikey, apikey, domain, id, delay)
    elif args['delete']:
        record_delete(secretapikey, apikey, domain, id)


def run(args):
    secretapikey = load_file(args['--secretapikey'])
    apikey = load_file(args['--apikey'])
    if args['ping']:
        ping(secretapikey, apikey)
    elif args['show_ip']:
        log(get_external_ip(secretapikey, apikey))
    elif args['record']:
        record(secretapikey, apikey, args)
    else:
        raise RuntimeError("Command not recognized. Arguments: {}".format(args))


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    try:
        run(args)
    except Exception as e:
        log("Oh no! Terminal exception: {}".format(e))
        exit(1)
