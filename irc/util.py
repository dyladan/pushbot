"""Contains utility functions for irc module"""

import requests
import json
import urllib.parse
import time


def buildmsg(command, arg=None, payload=None):
    """Given parameters builds a message to be sent to IRC server"""
    command = command.upper()

    if arg and payload:
        msg = "%s %s :%s\r\n" % (command, arg, payload)
    elif arg:
        msg = "%s %s\r\n" % (command, arg)
    elif payload:
        msg = "%s :%s\r\n" % (command, payload)
    else:
        raise Exception("IRCBadMessage")

    return msg.encode()

def shortlink(url):
    with open('config.json') as f:
        config = json.loads(f.read())
    print("shortening %s" % url)
    api = "https://api-ssl.bitly.com/v3/shorten/"
    access_token = config['bitly_key']

    #url = urllib.parse.quote(url)
    payload = {"longUrl": url, "access_token": access_token, "domain": "j.mp"}
    headers = {'content-type': 'application/json'}

    resp = requests.get(api, params=payload, headers=headers).json()
    print(resp)

    shorturl = resp['data']['url']

    return shorturl

def log(data):
    print("%s %s" % (time.ctime(), data))
