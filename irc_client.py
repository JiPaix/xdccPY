from asyncio import new_event_loop, set_event_loop, all_tasks
from typing import Union, List, Tuple
from time import sleep
import re
from ipaddress import IPv4Address
import os
import sys
import socket
import struct
from urllib.request import urlopen
import progressbar
import pydle
from timeout import TimeOut
from colored import fg, bg, attr
from python_utils.time import format_time
from job import Job
from io import BytesIO


def colorize(string, front=None, back=None, bold=False) -> str:
    string = str(string)
    if front:
        string = fg(str(front)) + string
    if back:
        string = fg(str(back)) + string
    if bold:
        string = attr('bold') + string
    string += attr('reset')
    return string


def eprint(message, padding=0, infotype='ok'):
    bold = attr('bold')
    green = bold + fg('green')
    cyan = bold + fg('cyan')
    red = bold + fg('red')
    reset = attr('reset')
    if infotype == 'ok':
        infotype = green + '\u2713 ' + reset
    elif infotype == 'info':
        infotype = cyan + '\u2139 ' + reset
    elif infotype == 'err':
        infotype = red + '\u0058 ' + reset
    message = infotype + message
    if padding > 0:
        message = '\u2937 '.rjust(padding, ' ') + message
    print(message, file=sys.stderr)


MyBaseClient = pydle.featurize(
    pydle.features.RFC1459Support,
    pydle.features.CTCPSupport,
    pydle.features.TLSSupport,
    pydle.features.ISUPPORTSupport
)


class Cli(MyBaseClient):
    def __init__(
        self,
        host: str,
        candidate: List[Job],
        port: int = 6667,
        nick: str = 'xdccJS',
        chan: Union[List[str], None] = None,
        path: Union[str, None] = None,
        retry: int = 1,
        verbose: bool = True,
        passive_port: int = 5001,
        wait: int = 0
    ):
        self.struct_format = b"!I"
        self.host = '{}:{}'.format(host, port)
        self.path = path
        self.chan = chan
        self.wait = wait
        self.resume = None
        self.passive_port = passive_port
        self.retry = retry
        self.verbose = verbose
        self.candidate = candidate
        self.max_retries = retry
        tmp_chan: List[str] = []
        if self.chan:
            for chans in self.chan:
                if chans[0] != '#':
                    tmp_chan.append('#' + chans)
                else:
                    tmp_chan.append(chans)
            if len(tmp_chan) > 0:
                self.chan = tmp_chan
            else:
                self.chan = None
        else:
            self.chan = None
        self.__retries = 0
        self.__pos = 0
        self.__timeout = TimeOut()
        self.ip = urlopen(
            'https://checkip.amazonaws.com').read().decode('utf8').strip()
        self.own_eventloop = new_event_loop()
        set_event_loop(self.own_eventloop)
        super().__init__(nick, realname='xdccJS')
        self.run(host, port=port, tls=False, tls_verify=False)

    async def on_connect(self):
        await super().on_connect()
        eprint('connected to {}'.format(colorize(self.host, front='244')))
        if self.chan:
            for chan in self.chan:
                await self.join(chan)
            eprint(
                'joined : {}'.format(
                    colorize(
                        ', '.join(
                            self.chan),
                        front='244')), padding=3)
        if self.wait:
            widgets = [
                progressbar.Timer(
                    format='  \u2937 {} waiting: %(elapsed)s / {}'.format(
                        colorize(
                            '\u2139', front='cyan', bold=True), format_time(
                            self.wait)))]
            for i in progressbar.progressbar(
                    range(100), redirect_stderr=True, widgets=widgets):
                sleep(self.wait / 100)
            # eprint('done sleeping')
        await self.dl()

    async def dl(self):
        if len(self.candidate) > 0:
            if self.__pos > len(self.candidate[0].queue) - 1:
                self.candidate[0].trigger('done', self.candidate[0].show())
                del self.candidate[0]
                self.__pos = 0
                await self.dl()
            else:
                if self.__retries == 0:
                    eprint('sending command: {} {} {} {}'.format(
                        colorize('/MSG', front='244'),
                        colorize(self.candidate[0].id, front='13'),
                        colorize('xdcc send', front='244'),
                        colorize(
                            self.candidate[0].queue[self.__pos], front='yellow'
                        ),
                        front='yellow'), 4)
                self.__timeout.start(
                    30,
                    self.handle_retry,
                    'no response'.format(
                        colorize(
                            self.candidate[0].id,
                            front='yellow')),
                    None,
                    padding=6)
                self.candidate[0].now = self.candidate[0].queue[self.__pos]
                await self.message(
                    self.candidate[0].id,
                    'xdcc send ' + str(self.candidate[0].queue[self.__pos])
                )
        else:
            await self.disconnect()

    async def on_raw(self, message):
        await super().on_raw(message)
        if len(message.params) > 1:
            match = re.search("{}DCC .*{}".format(chr(1),
                                                  chr(1)), message.params[1])
            self.candidate[0].source = message.source
            if match:
                regexp = r'(?:[^\s"]+|"[^"]*")+'
                match = match.group(0)
                match = re.findall(regexp, match.replace(chr(1), ''))
                if match[1] == 'SEND':
                    self.__timeout.stop()
                    res = {
                        'type': match[1],
                        'from': re.sub('!.+$', '', self.candidate[0].source),
                        'file': match[2].replace('"', ''),
                        'ip': str(IPv4Address(int(match[3]))),
                        'port': int(match[4]),
                        'position': 0,
                        'length': int(match[5]),
                        'token': None
                    }
                    if len(match) > 6:
                        res['token'] = int(match[6])
                    if isinstance(self.path, str):
                        res['file_path'] = os.path.normpath(
                            self.path + '/' + res['file'])
                        if os.path.exists(res['file_path']):
                            position = os.path.getsize(res['file_path'])
                            if res['length'] == position:
                                position = position - 8192
                            if re.search(' ', res['file']):
                                quoted_filename = '"' + res['file'] + '"'
                            else:
                                quoted_filename = res['file']
                            eprint(
                                'resuming: {}'.format(
                                    colorize(res['file'], front='cyan')
                                ),
                                6,
                                infotype='info'
                            )
                            self.__timeout.start(
                                15,
                                self.handle_retry,
                                "bot doesn't support transfert resuming",
                                None,
                                padding=6
                            )
                            await self.ctcp(
                                res['from'],
                                'DCC RESUME',
                                quoted_filename + ' ' +
                                str(res['port']) + ' ' + str(position)
                            )
                            self.resume = res
                        else:
                            self.__timeout.start(
                                5,
                                self.handle_retry,
                                'cannot connect',
                                None,
                                padding=6
                            )
                            eprint(
                                'downloading : {}'.format(
                                    colorize(res['file'], front='cyan')
                                ),
                                6,
                                infotype='info'
                            )
                            await self.handle_dl(res)
                            self.resume = None
                            await self.dl()
                    else:
                        self.__timeout.start(
                            5,
                            self.handle_retry,
                            'cannot connect',
                            None,
                            padding=6
                        )
                        await self.handle_dl(res)
                        self.resume = None
                        await self.dl()
                elif match[1] == 'ACCEPT':
                    if self.resume:
                        res = {
                            'type': match[1],
                            'from': re.sub(
                                '!.+$', '', self.candidate[0].source
                            ),
                            'file': match[2].replace('"', ''),
                            'file_path': str(self.resume['file_path']),
                            'ip': str(self.resume['ip']),
                            'port': int(match[3]),
                            'position': int(match[4]),
                            'length': int(self.resume['length']),
                            'token': None
                        }
                        if self.resume['token']:
                            res['token'] = self.resume['token']
                        self.__timeout.start(
                            5,
                            self.handle_retry,
                            'cannot connect',
                            None,
                            padding=6
                        )
                        await self.handle_dl(res)
                        self.resume = None
                        await self.dl()

    async def handle_dl(self, res):
        allsockets = []
        if self.path:
            stream = open(res['file_path'], 'ab')
            stream.seek(res['position'])
            stream.truncate()
        else:
            stream = BytesIO()
        allsockets.append(stream)
        if res['port'] == 0:
            # eprint('passive dcc')
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('', self.passive_port))
            server.listen(1)
            allsockets.append(server)
            if re.search(' ', res['file']):
                quoted_filename = '"' + res['file'] + '"'
            else:
                quoted_filename = res['file']
            message = 'DCC SEND {} {} {} {} {}'.format(
                quoted_filename,
                int(IPv4Address(self.ip)),
                self.passive_port,
                res['length'],
                res['token']
            )
            await self.ctcp(res['from'], message)
            # eprint(res['from'], message)
            while True:
                connection, address = server.accept()
                allsockets.append(connection)
                break
        else:
            # eprint('active dcc')
            connection = socket.socket()
            connection.connect((res['ip'], res['port']))
            connection.settimeout(5)
            allsockets.append(connection)
        received = 0
        total: int = res['length'] - res['position']
        widgets = [
            '      \u2937 ',
            progressbar.Bar(
                marker='=',
                left='[',
                right=']'),
            ' ',
            progressbar.ETA(),
            ' @ ',
            progressbar.FileTransferSpeed(),
            ' - ',
            progressbar.Percentage(),
        ]
        bar = progressbar.ProgressBar(
            widgets=widgets,
            max_value=total,
            redirect_stderr=True,
            term_width=80
        ).start()
        while received < total:
            self.__timeout.start(
                5,
                self.handle_retry,
                'timeout: stopped receiving data',
                allsockets,
                padding=6)
            data = connection.recv(2**14)
            if not self.path:
                self.candidate[0].trigger(
                    'pipe', data, False, received, total, res)
            stream.write(data)
            received += len(data)
            bar.update(received)
            payload = struct.pack(self.struct_format, received)
            connection.send(payload)
            if received >= total:
                for sock in allsockets:
                    sock.close()
                bar.finish()
                if not self.path:
                    self.candidate[0].trigger(
                        'pipe', None, True, received, total, res)
                self.__pos += 1
                self.candidate[0].done.append(res['file'])
                self.__timeout.stop()
                self.__retries = 0
                self.candidate[0].trigger('downloaded', res)
                eprint('done.', padding=9)

    async def on_unknown(self, message):
        await super().on_unknown(message)
        pass

    async def handle_retry(self, message, streams, padding=0):
        self.candidate[0].trigger('error', message, self.candidate[0].show())
        eprint(message, padding=padding, infotype='err')
        if streams:
            for stream in streams:
                stream.close()
        if self.__retries < self.max_retries:
            self.__retries += 1
            eprint(
                'retrying : {}/{}'.format(
                    self.__retries,
                    self.max_retries
                ),
                padding=6,
                infotype='info'
            )
            await self.dl()
        else:
            eprint(
                'max attempts: skipping pack {}'.format(
                    colorize(self.candidate[0].now, front='yellow'),
                ),
                padding=8,
                infotype='err'
            )
            self.candidate[0].failed.append(self.candidate[0].now)
            self.__pos += 1
            self.__retries = 0
            await self.dl()
