import asyncio
import websockets
import json

import irc.util
import irc.aiopb


class IRCProtocol(asyncio.Protocol):
    def __init__(self, config, loop):
        self.config = config
        self.loop = loop
        self.response_data = bytes()

    def connection_made(self, transport):
        irc.util.log("connection made")
        self.transport = transport
        asyncio.async(self.monitor_pb())
        self.setnick(self.config['nick'])
        self.setuser(self.config['user'], self.config['name'])
        self.join(self.config['channel'])

    def data_received(self, data):
        self.response_data = data
        lines = self.response_data.decode().splitlines()
        for line in lines:
            if line[:4] == 'PING':
                pong_server = line[6:]
                pong = irc.util.buildmsg("PONG", pong_server)
                self.transport.write(pong)

    def setnick(self, nick):
        irc.util.log("Set nick: %s" % nick)
        nick = irc.util.buildmsg("NICK", nick)
        self.transport.write(nick)

    def setuser(self, user, name):
        irc.util.log("Set user: %s" % user)
        user = irc.util.buildmsg("USER", "%s 0 *" % user, name)
        self.transport.write(user)

    def join(self, channel):
        irc.util.log("join %s" % channel)
        chan = irc.util.buildmsg("JOIN", channel)
        self.transport.write(chan)

    def privmsg(self, msg):
        """Send a PRIVMSG"""
        irc.util.log("saying: %s" % msg)
        tail = None
        if len(msg) > 360:
            tail = msg[360:]
            msg = msg[:360]
        data = irc.util.buildmsg("PRIVMSG", self.config['channel'], msg)
        self.transport.write(data)
        if tail:
            self.privmsg(chan, tail)

    @asyncio.coroutine
    def monitor_pb(self):
        first_run = True
        obj = {}
        ident = self.config['pb_key']
        url = "wss://stream.pushbullet.com/websocket/%s" % ident
        websocket = yield from websockets.connect(url)
        irc.util.log("websocket %s connected" % websocket)
        last = 0
        while True:
            obj = yield from websocket.recv()
            if obj is None:
                irc.util.log("websocket %s closed" % websocket)
                irc.util.log("reconnecting")
                websocket = yield from websockets.connect(url)
                irc.util.log("websocket %s connected" % websocket)
            obj = json.loads(obj)
            if first_run or obj['type'] == 'tickle' and obj['subtype'] == 'push':
                first_run = False
                irc.util.log("event stream recieved %s" % obj)
                pushes = yield from irc.aiopb.get_pushes(ident, last)
                #pushes = irc.pb.get_pushes(ident, last)
                irc.util.log("%s new pushes" % len(pushes))
                if len(pushes) > 0 and 'modified' in pushes[0]:
                    last = pushes[0]['modified']
                for push in pushes:
                    ret = yield from irc.aiopb.push_to_s(push)
                    self.privmsg(ret)
                    status = yield from irc.aiopb.dismiss_push(push, ident)
                    if status == 200:
                        irc.util.log("dismissed %s" % push['iden'])
                    else:
                        irc.util.log("error dismissing %s: %s" % (push['iden'], status))


def main():
    with open('config.json') as f:
        config = json.loads(f.read())
    host = config['host']
    port = config['port']

    loop = asyncio.get_event_loop()

    bot = IRCProtocol(config, loop)
    coro = loop.create_connection(lambda: bot, host=host, port=port)

    loop.run_until_complete(coro)
    loop.run_forever()

if __name__ == "__main__":
    main()
