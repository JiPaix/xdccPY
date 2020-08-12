
from random import seed
from random import randint

import threading
from typing import Union, Iterable
import sys
from irc_client import Cli as cli

# log helper


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# xdcc
class xdcc():
    def __init__(
        self,
        host: str,
        port: int = 6667,
        nick: str = 'xdccJS',
        chan: Union[Iterable[str], None] = None,
        path: Union[str, None] = None,
        retry: int = 1,
        verbose: bool = True,
        passive_port: int = 5001,
        wait: int = 0,
        randomize_nick: bool = True
    ):
        self.candidate = []
        self.cli = None
        if randomize_nick:
            seed(nick.__le__)
            random = randint(0, 999)
            nick = nick + str(random)
        self.opts = (host, port, nick, chan, path,
                     retry, verbose, passive_port, wait)

    def download(
            self,
            bot: str,
            package: Union[
                Iterable[str],
                Iterable[int],
                int,
                str
            ]
    ):
        if isinstance(package, str):
            package = self.__parse_package(package)
        elif isinstance(package, (tuple, list)):
            newpackage = []
            for pack in package:
                newpackage.append(int(pack))
            package = newpackage
        elif isinstance(package, int):
            package = [package]
        dejavu = list(filter(lambda dl: dl.id == bot, self.candidate))
        if len(dejavu) > 0:
            bot_index = next(
                (index for (
                    index,
                    d) in enumerate(
                    self.candidate) if d.id == bot),
                None)
            self.candidate[bot_index].queue.extend(package)
        else:
            self.candidate.append(Candidate(bot, package))
        if self.cli is None or self.cli.is_alive() is False:
            self.cli = threading.Thread(
                target=cli,
                args=(self.opts[0], self.candidate),
                kwargs={
                    'port': self.opts[1],
                    'nick': self.opts[2],
                    'chan': self.opts[3],
                    'path': self.opts[4],
                    'retry': self.opts[5],
                    'verbose': self.opts[6],
                    'passive_port': self.opts[7],
                    'wait': self.opts[8]
                }
            )
            self.cli.start()
            if len(self.candidate) > 0:
                eprint(self.candidate[0].queue)

    def __parse_package(self, package: str):
        result = []
        split = package.replace(' ', '').split(',')
        for pack in split:
            if '-' in pack:
                start, end = (x for x in pack.split('-'))
                end = end or start
                result.extend(range(int(start), int(end) + 1))
            else:
                result.append(int(pack))
        return sorted(result)


class Candidate():
    def __init__(self, bot: str, packages: Iterable[int]):
        self.id = bot
        self.queue = packages

##############
# HOW TO USE #
##############
# d = xdcc('irc.rizon.net', chan=['#xdccjs'], path='download')
# d.download('ginpachi-sensei', '3')
# d.download('ginpachi-sensei', '4')
