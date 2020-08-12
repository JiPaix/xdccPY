from asyncio import new_event_loop, set_event_loop, all_tasks
from typing import Union, Iterable
import time
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


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


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
        candidate: list,
        port: int = 6667,
        nick: str = 'xdccJS',
        chan: Union[Iterable[str], None] = None,
        path: Union[str, None] = None,
        retry: int = 1,
        verbose: bool = True,
        passive_port: int = 5001,
        wait: int = 0
    ):
        self.struct_format = b"!I"
        self.path = path
        self.chan = chan
        self.wait = wait
        self.resume = None
        self.passive_port = passive_port
        self.retry = retry
        self.verbose = verbose
        self.candidate = candidate
        self.max_retries = retry
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
        if self.chan:
            for chan in self.chan:
                if chan[0] == '#':
                    await self.join(chan)
                    eprint('joined: ' + chan)
                else:
                    await self.join('#' + chan)
                    eprint('joined: #' + chan)
        if self.wait:
            eprint('sleeping for ' + str(self.wait))
            time.sleep(self.wait)
            eprint('done sleeping')
        await self.dl()

    async def dl(self):
        if len(self.candidate) > 0:
            if self.__pos > len(self.candidate[0].queue) - 1:
                del self.candidate[0]
                self.__pos = 0
                await self.dl()
            else:
                eprint('xdcc send ' + str(self.candidate[0].queue[self.__pos]))

                # self.__timeout.start(15, print, 'no initial response')
                await self.message(
                    self.candidate[0].id,
                    'xdcc send ' + str(self.candidate[0].queue[self.__pos])
                )
        else:
            for task in all_tasks():
                task.cancel()
            await self.disconnect()

    async def on_raw(self, message):
        await super().on_raw(message)
        if len(message.params) > 1:
            match = re.search("{}DCC .*{}".format(chr(1),
                                                  chr(1)), message.params[1])
            source = message.source
            # self.__timeout.stop()
            if match:
                regexp = r'(?:[^\s"]+|"[^"]*")+'
                match = match.group(0)
                match = re.findall(regexp, match.replace(chr(1), ''))
                if match[1] == 'SEND':
                    eprint('dcc reponse initial')
                    res = {
                        'type': match[1],
                        'from': re.sub('!.+$', '', source),
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
                            eprint(str(res['length']) + ' vs ' + str(position))
                            if res['length'] == position:
                                eprint('same file')
                                position = position - 8192
                            if re.search(' ', res['file']):
                                quoted_filename = '"' + res['file'] + '"'
                            else:
                                quoted_filename = res['file']
                            eprint('demande de resume')
                            eprint('DCC RESUME', quoted_filename + ' ' +
                                   str(res['port']) + ' ' + str(position))
                            await self.ctcp(
                                res['from'],
                                'DCC RESUME',
                                quoted_filename + ' ' +
                                str(res['port']) + ' ' + str(position)
                            )
                            self.resume = res
                        else:
                            await self.handle_dl(res)
                            self.resume = None
                            self.__pos = self.__pos + 1
                            await self.dl()
                    else:
                        await self.handle_dl(res)
                        self.resume = None
                        self.__pos = self.__pos + 1
                        await self.dl()
                elif match[1] == 'ACCEPT':
                    print('resume accepte')
                    if self.resume:
                        res = {
                            'type': match[1],
                            'from': re.sub('!.+$', '', source),
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
                        await self.handle_dl(res)
                        self.resume = None
                        self.__pos = self.__pos + 1
                        await self.dl()

    async def handle_dl(self, res):
        eprint('start dl')
        if self.path:
            stream = open(res['file_path'], 'ab')
            stream.seek(res['position'])
            stream.truncate()
        else:
            stream = sys.stdout.buffer
        if res['port'] == 0:
            eprint('passive dcc')
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('', self.passive_port))
            server.listen(1)
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
            eprint(res['from'], message)
            while True:
                connection, address = server.accept()
                eprint("Connected from", address)
                break
        else:
            eprint('active dcc')
            connection = socket.socket()
            connection.connect((res['ip'], res['port']))
            connection.settimeout(5)
        received = 0
        total = res['length'] - res['position']
        widgets = [
            'Downloading: ', progressbar.Percentage(),
            ' @ ', progressbar.FileTransferSpeed(),
            ' ', progressbar.Bar(marker='#', left='[', right=']'),
            ' ', progressbar.ETA(),
        ]
        bar = progressbar.ProgressBar(
            widgets=widgets,
            max_value=total,
            redirect_stderr=True,
            term_width=80
        ).start()
        while received < total:
            data = connection.recv(2**14)
            received += len(data)
            bar.update(received)
            stream.write(data)
            payload = struct.pack(self.struct_format, received)
            connection.send(payload)
            if received >= total:
                connection.close()
                stream.close()
                bar.finish()
        eprint('im done')

    async def on_unknown(self, message):
        pass
