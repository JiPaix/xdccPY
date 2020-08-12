from random import seed
from random import randint
import threading
from typing import Any, Dict, Union, Iterable, List
import sys
from irc_client import Cli
from job import Job


class xdcc():
    def __init__(
        self,
        host: str,
        port: int = 6667,
        nick: str = 'xdccJS',
        chan: Union[Iterable[str], None] = None,
        path: Union[str, None] = None,
        retry: int = 1,
        verbose: bool = False,
        passive_port: int = 5001,
        wait: int = 0,
        randomize_nick: bool = True
    ):
        self.candidate: List[Job] = []
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
    ) -> Job:
        index = 0
        retpackage: List[int] = []
        if isinstance(package, str):
            retpackage = self.__parse_package(package)
        elif isinstance(package, (tuple, list)):
            newpackage: List[int] = []
            for pack in package:
                newpackage.append(int(pack))
            retpackage = newpackage
        elif isinstance(package, int):
            retpackage = [package]

        dejavu = list(filter(lambda dl: dl.id == bot, self.candidate))
        if len(dejavu) > 0:
            bot_index = next(
                (index for (
                    index,
                    d) in enumerate(
                    self.candidate) if d.id == bot),
                None)
            index = bot_index or 0
            self.candidate[index].queue.extend(retpackage)
        else:
            self.candidate.append(Job(bot, retpackage))
        if self.cli is None or self.cli.is_alive() is False:
            self.cli = threading.Thread(
                target=Cli,
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
        return self.candidate[index]

    def __parse_package(self, package: str) -> List[int]:
        result: List[int] = []
        split = package.replace(' ', '').split(',')
        for pack in split:
            if '-' in pack:
                start, end = (x for x in pack.split('-'))
                end = end or start
                result.extend(range(int(start), int(end) + 1))
            else:
                result.append(int(pack))
        return sorted(result)
