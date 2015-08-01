import asyncio
import websockets
import json

from irc.util import buildmsg
import irc.pb

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
        self.transport = transport
        asyncio.async(self.monitor_pb())
        self.setnick(self.nick)
        self.setuser(self.user, self.name)
        if self.channel:
            self.join(self.channel)

    def setnick(self, nick):
        nick = buildmsg("NICK", nick)
        self._send(nick)

    def setuser(self, user, name):
        user = buildmsg("USER", "%s 0 *" % user, name)
        self._send(user)

    def join(self, channel):
        chan = buildmsg("JOIN", channel)
        self._send(chan)

    def privmsg(self, msg):
        """Send a PRIVMSG"""
        tail = None
        if len(msg) > 360:
            tail = msg[360:]
            msg = msg[:360]
        data = buildmsg("PRIVMSG", self.channel, msg)
        self._send(data)
        if tail:
            self.privmsg(chan, tail)

    def data_received(self, data):
        self.response_data = data
        lines = self.response_data.decode().splitlines()
        for line in lines:
            if line[:4] == 'PING':
                pong_server = line[6:]
                pong = buildmsg("PONG", pong_server)
                self.transport.write(pong)

    def _send(self, data):
        print("> %s" % data)
        self.transport.write(data)

    @asyncio.coroutine
    def monitor_pb(self):
        ident = self.config['pb_key']
        websocket = yield from websockets.connect("wss://stream.pushbullet.com/websocket/%s" % ident)
        last = 0
        while True:
            obj = yield from websocket.recv()
            if obj is None:
                raise Exception('websocket closed')
            obj = json.loads(obj)
            if obj['type'] == 'tickle' and obj['subtype'] == 'push':
                print(obj)
                pushes = irc.pb.get_pushes(ident, last)
                if len(pushes) > 0 and 'modified' in pushes[0]:
                    last = pushes[0]['modified']
                    print('last modified %s' % last)
                for push in pushes:
                    ret = irc.pb.push_to_s(push)
                    self.privmsg(ret)
                    irc.pb.dismiss_push(push, ident)


def main(host, nick, user, name, config={}, channel=None):
    bot = IRCProtocol(nick, user, name, config, channel)
    asyncio.async(loop.create_connection(lambda: bot, host=host, port=6667))

with open('config.json') as f:
    config = json.loads(f.read())

loop.call_soon(main, "127.0.0.1", 'pushbot', 'pushbot', 'pushbot', config, "#geekboy")
loop.run_forever()
