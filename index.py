import pydle
from random import seed
from random import randint
import time
import threading 
from asyncio import new_event_loop, get_event_loop, set_event_loop, all_tasks, sleep
import re
from typing import List, Set, Dict, Tuple, Optional, Union, Iterable
from ipaddress import IPv4Address
import os
import sys
import socket
import struct
import urllib.request
import progressbar
from functools import wraps

# log helper
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# timeout function
def delay(delay=0.):
    def wrap(f):
        @wraps(f)
        def delayed(*args, **kwargs):
            timer = threading.Timer(delay, f, args=args, kwargs=kwargs)
            timer.start()
        return delayed
    return wrap

class Timer():
    toClearTimer = False
    def setTimeout(self, fn, time, *args):
        isInvokationCancelled = False
        @delay(time)
        def some_fn():
                if (self.toClearTimer is False):
                        fn(*args)
                else:
                    print('canceled')        
        some_fn()
        return isInvokationCancelled
    def setClearTimer(self):
        self.toClearTimer = True


MyBaseClient = pydle.featurize(pydle.features.RFC1459Support, pydle.features.CTCPSupport, pydle.features.TLSSupport, pydle.features.ISUPPORTSupport)
# irc client
class cli(MyBaseClient):
    def __init__(self, host:str, candidate:list, port:int=6667, nick:str='xdccJS', chan:Union[Iterable[str], None]=None, path:Union[str,None]=None, retry:int=1, verbose:bool=True, passivePort:int=5001, wait:int=0):
        self.struct_format = b"!I"
        self.path = path
        self.chan = chan
        self.wait = wait
        self.passivePort = passivePort
        self.retry = retry
        self.verbose = verbose
        self.candidate = candidate
        self.max_retries = retry
        self.__retries =0
        self.__pos = 0
        self.__timeout = Timer()
        self.ip = urllib.request.urlopen('https://checkip.amazonaws.com').read().decode('utf8').strip()
        self.own_eventloop = new_event_loop()
        set_event_loop(self.own_eventloop)
        super().__init__(nick, realname='xdccJS')
        self.run(host, port=port, tls=False, tls_verify=False)
    async def on_connect(self):
        await super().on_connect()
        if self.chan:
            for chan in self.chan:
                if(chan[0] == '#'):
                    await self.join(chan)
                    eprint('joined: '+chan)
                else:
                    await self.join('#'+chan)
                    eprint('joined: #'+chan)
        if self.wait:
            eprint('sleeping for '+str(self.wait))
            time.sleep(self.wait)
            eprint('done sleeping')
        await self.dl()

    async def dl(self):
        if len (self.candidate) > 0:
            if(self.__pos > len(self.candidate[0].queue)-1):
                del self.candidate[0]
                self.__pos = 0
                await self.dl()
            else:
                eprint('xdcc send '+str(self.candidate[0].queue[self.__pos]))
                self.__timeout.setTimeout(eprint, 15, 'No Initial response')
                await self.message(self.candidate[0].id, 'xdcc send '+str(self.candidate[0].queue[self.__pos]))
        else:
            for task in all_tasks():
                task.cancel()
            await self.disconnect()

    async def on_raw(self, message):
        await super().on_raw(message)
        if len(message.params) > 1:
            match = re.search("{}DCC .*{}".format(chr(1),chr(1)), message.params[1])
            source = message.source
            self.__timeout.setClearTimer()
            if match:
                regexp = '(?:[^\s"]+|"[^"]*")+'
                match = match.group(0)
                match = re.findall(regexp, match.replace(chr(1), ''))
                if match[1] == 'SEND':
                    eprint('dcc reponse initial')
                    res = {
                        'type': match[1],
                        'from': re.sub('!.+$', '', source),
                        'file':match[2].replace('"', ''),
                        'ip': str(IPv4Address(int(match[3]))),
                        'port': int(match[4]),
                        'position': 0,
                        'length': int(match[5]),
                        'token': None
                            }
                    if(len(match) > 6):
                        res['token'] = int(match[6])
                    if type(self.path) is str:
                        res['file_path'] = os.path.normpath(self.path+'/'+res['file'])
                        if os.path.exists(res['file_path']):
                            position = os.path.getsize(res['file_path'])
                            eprint(str(res['length'])+' vs '+ str(position))
                            if(res['length'] == position):
                                eprint('same file')
                                position = position - 8192
                            if re.search(' ', res['file']):
                                quotedFilename = '"'+res['file']+'"'
                            else:
                                quotedFilename = res['file']
                            eprint('demande de resume')
                            eprint('DCC RESUME', quotedFilename+' '+str(res['port'])+' '+str(position))
                            await self.ctcp(res['from'], 'DCC RESUME', quotedFilename+' '+str(res['port'])+' '+str(position))
                            self.resume = res
                        else:
                            await self.handle_dl(res)
                            self.resume = None
                            self.__pos = self.__pos+1
                            await self.dl()
                    else:
                        await self.handle_dl(res)
                        self.resume = None
                        self.__pos = self.__pos+1
                        await self.dl()
                elif match[1] == 'ACCEPT':
                    print('resume accepte')
                    if self.resume:
                        res = {
                            'type': match[1],
                            'from': re.sub('!.+$', '', source),
                            'file':match[2].replace('"', ''),
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
                        self.__pos = self.__pos+1
                        await self.dl()
    async def handle_dl(self, res):
        eprint('start dl')
        if self.path:
            f = open(res['file_path'], 'ab')
            f.seek(res['position'])
            f.truncate()
        else:
            f = sys.stdout.buffer
        if res['port'] == 0:
            eprint('passive dcc')
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('', self.passivePort))
            server.listen(1)
            if re.search(' ', res['file']):
                quotedFilename = '"'+res['file']+'"'
            else:
                quotedFilename = res['file']
            await self.ctcp(res['from'], 'DCC SEND', quotedFilename+' '+str(int(IPv4Address(self.ip)))+' '+str(self.passivePort)+' '+str(res['length'])+' '+str(res['token']))
            eprint(res['from'], 'DCC SEND', quotedFilename+' '+str(int(IPv4Address(self.ip)))+' '+str(self.passivePort)+' '+str(res['length'])+' '+str(res['token']))
            while True:
                s,address = server.accept()
                eprint("Connected from", address)
                break
        else:
            eprint('active dcc')
            s = socket.socket()
            s.connect((res['ip'], res['port']))
            s.settimeout(5)
        received = 0
        total = res['length']-res['position']
        widgets = [
            'Downloading: ', progressbar.Percentage(),
            ' @ ', progressbar.FileTransferSpeed(),
            ' ', progressbar.Bar(marker='#', left='[', right=']'),
            ' ', progressbar.ETA(),
        ]
        bar = progressbar.ProgressBar(widgets=widgets, max_value=total, redirect_stderr=True, term_width=80).start()
        while received < total:
            data = s.recv(2**14)
            received += len(data)
            bar.update(received)
            f.write(data)
            payload = struct.pack(self.struct_format, received)
            s.send(payload)
            if received >= total:
                s.close()
                f.close()
                bar.finish()
        eprint('im done')
    async def on_unknown(self, message):
        pass
# xdcc
class xdcc():
    def __init__(self, host:str, port:int=6667, nick:str='xdccJS', chan:Union[Iterable[str], None]=None, path:Union[str,None]=None, retry:int=1, verbose:bool=True, passivePort:int=5001, wait:int=0, randomizeNick:bool=True):
        self.candidate = []
        self.candidateClass = []
        self.cli = None
        self.pool = pydle.ClientPool()
        if randomizeNick:
            seed(nick.__le__)
            random = randint(0, 999)
            nick = nick+str(random)
        self.opts = (host, port, nick, chan, path, retry, verbose, passivePort, wait)
    def download(self, bot:str, package:Union[Iterable[str], Iterable[int]]):
        if type(package) is str:
            package = self.__parse_package(package)
        elif type(package) is tuple or type(package) is list:
            newpackage = []
            for pack in package:
                if type(pack) is str:
                    newpackage.append(int(pack))
                elif type(pack) is int:
                    newpackage.append(pack)
            package = newpackage
        elif type(package) is int:
            package = [package]
        dejavu = list(filter(lambda dl: dl.id == bot, self.candidate))
        if len(dejavu) > 0:
            bot_index = next((index for (index, d) in enumerate(self.candidate) if d.id == bot), None)
            self.candidate[bot_index].queue = self.candidate[bot_index].queue+package
        else:
            self.candidate.append(Candidate(bot, package))
        if self.cli is None or self.cli.is_alive() is False:
            self.cli = threading.Thread(target=cli,args=(self.opts[0], self.candidate), kwargs={'port':self.opts[1], 'nick':self.opts[2], 'chan' : self.opts[3], 'path' : self.opts[4], 'retry' : self.opts[5], 'verbose':self.opts[6], 'passivePort':self.opts[7], 'wait':self.opts[8]})
            self.cli.start()
            if len(self.candidate)>0:
                eprint(self.candidate[0].queue)
    def __parse_package(self, package:str):
        result = []
        split = package.replace(' ', '').split(',')
        for pack in split:
            if '-' in pack:
                a_range = pack.split('-')
                start = int(a_range[0])
                end = int(a_range[1])+1
                result = result + list(range(start, end))
            else:
                result.append(int(pack))
        return sorted(result)

class Candidate():
    def __init__(self, bot:str, packages):
        self.id:str = bot
        self.queue:Iterable[int] = packages




d = xdcc('irc.rizon.net', chan=['#xdccjs'], path='download')
d.download('ginpachi-sensei', '3')



