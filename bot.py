import asyncio
import websockets
import json

import irc.pb
import irc.util

loop = asyncio.get_event_loop()

class IRCProtocol(asyncio.Protocol):
    def __init__(self, nick, user, name, config={}, channel=None):
        self.nick = nick
        self.user = user
        self.name = name
        self.channel = channel
        self.config = config
        self.response_data = bytes()

    def connection_made(self, transport):
        irc.util.log("connection made")
        self.transport = transport
        asyncio.async(self.monitor_pb())
        self.setnick(self.nick)
        self.setuser(self.user, self.name)
        if self.channel:
            self.join(self.channel)

    def setnick(self, nick):
        irc.util.log("Set nick: %s" % nick)
        nick = irc.util.buildmsg("NICK", nick)
        self._send(nick)

    def setuser(self, user, name):
        irc.util.log("Set user: %s" % user)
        user = irc.util.buildmsg("USER", "%s 0 *" % user, name)
        self._send(user)

    def join(self, channel):
        irc.util.log("join %s" % channel)
        chan = irc.util.buildmsg("JOIN", channel)
        self._send(chan)

    def privmsg(self, msg):
        """Send a PRIVMSG"""
        irc.util.log("saying: %s" % msg)
        tail = None
        if len(msg) > 360:
            tail = msg[360:]
            msg = msg[:360]
        data = irc.util.buildmsg("PRIVMSG", self.channel, msg)
        self._send(data)
        if tail:
            self.privmsg(chan, tail)

    def data_received(self, data):
        self.response_data = data
        lines = self.response_data.decode().splitlines()
        for line in lines:
            if line[:4] == 'PING':
                pong_server = line[6:]
                pong = irc.util.buildmsg("PONG", pong_server)
                self.transport.write(pong)

    def _send(self, data):
        self.transport.write(data)

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
                #raise Exception('websocket closed')
            obj = json.loads(obj)
            if first_run or obj['type'] == 'tickle' and obj['subtype'] == 'push':
                irc.util.log("event stream recieved %s" % obj)
                pushes = irc.pb.get_pushes(ident, last)
                irc.util.log("%s new pushes" % len(pushes))
                if len(pushes) > 0 and 'modified' in pushes[0]:
                    last = pushes[0]['modified']
                for push in pushes:
                    ret = irc.pb.push_to_s(push)
                    self.privmsg(ret)
                    irc.pb.dismiss_push(push, ident)


def main(host, nick, user, name, config={}, channel=None):
    bot = IRCProtocol(nick, user, name, config, channel)
    asyncio.async(loop.create_connection(lambda: bot, host=host, port=6667))

if __name__ == "__main__":
    with open('config.json') as f:
        config = json.loads(f.read())

    loop.call_soon(main, "127.0.0.1", 'pushbot', 'pushbot', 'pushbot', config, "#geekboy")
    loop.run_forever()
