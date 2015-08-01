import requests
import json
from irc.util import shortlink

def get_pushes(ident, modified_after=0, active='true'):
    r = requests.get("https://api.pushbullet.com/v2/pushes?modified_after=%s&active=%s" % (modified_after, active), headers={'Authorization': 'Bearer %s' % ident})
    print('%s pushes pulled down from server' % len(r.json()['pushes']))
    pushes = [p for p in r.json()['pushes'] if not p['dismissed']]
    print('%s pushes not dismissed' % len(pushes))
    return pushes

def push_to_s(push):
    sender = push['sender_email_normalized']
    if push['type'] == 'note':
        return('<%s> %s' % (sender, push['body']))
    elif push['type'] == 'link':
        title = push['title']
        url = push['url']
        shorturl = shortlink(url)
        body = push['body']
        return('<%s> (%s) - %s - %s' % (sender, title, shorturl, body))
    elif push['type'] == 'file':
        filename = push['file_name']
        url = push['file_url']
        shorturl = shortlink(url)
        return('<%s> (%s) - %s' % (sender, filename, shorturl))

def dismiss_push(push, ident):
    payload = {'dismissed': True}
    headers = {'Authorization': 'Bearer %s' % ident, 'Content-Type': 'application/json'}
    r = requests.post("https://api.pushbullet.com/v2/pushes/%s" % push['iden'], headers=headers, data=json.dumps(payload))
    print(r.status_code)
    print('dismissed push %s' % push['iden'])

