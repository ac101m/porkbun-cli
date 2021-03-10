'''[porkbun dynamic DNS updater]
Dynamic IP got you down?
Here's an updater for domains hosted by porkbun.com.

Usage:
  porkbun-updater (-h | --help)
  porkbun-updater ping
  porkbun-updater update [options]
  porkbun-updater run [options]

Options:
  -h --help             Display this help message.
  -d --delay=<seconds>  How frequently should the updater check for IP address changes.
  -k --keys=<path>      Path to api key file. Make sure to set sensible permissions on this! [default: keys.cfg]
  -a --api-keyfile=<path>   Path to api key file. [default: api-key]
  -s --secret-keyfile=<path>    Path to secret api key file. [default: secret-key]
'''

import docopt
import requests


def load_key(path):
    try:
        return open(path, 'r').read().strip()
    except Exception as e:
        print("Could not open keyfile! {}".format(e))
        exit(1)


def ping(api_key, secret_key):
    response = requests.post(
        'https://porkbun.com/api/json/v3/ping',
        json={"secretapikey": secret_key, "apikey": api_key}
    )

    if response.status_code != 200:
        print("Oh no! Got status {} when trying to ping porkbun.".format(r.status_code))
        exit(1)

    json = response.json()

    print("Porkbun says {}!".format(json['status']))

    if json['status'] != 'SUCCESS':
        print(json['message'])


def ip_has_changed():
    return False


def run(args):
    api_key = load_key(args['--api-keyfile'])
    private_key = load_key(args['--secret-keyfile'])

    if args['ping'] == True:
        ping(api_key, private_key)


if __name__ == '__main__':
    run(docopt.docopt(__doc__))
