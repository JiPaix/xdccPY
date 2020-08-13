#############################
# Directly pipe data to VLC #
#############################

import subprocess
import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from index import xdcc  # noqa


# Starting VLC (for windows)
cmdline = ['C:\\Program Files\\VideoLAN\\VLC\\vlc.exe', '-']
VLC = subprocess.Popen(cmdline, stdin=subprocess.PIPE)


def write2stream(data, done, received, total, res):
    global VLC
    if VLC.poll() is None:  # checking if VLC hasn't been closed
        try:
            VLC.stdin.write(data)
        except BrokenPipeError:  # kill process if VLC is closed
            VLC.kill()


# Path must be None in order to enable piping
xdccPY = xdcc('irc.server.net', path=None)
xdccPY.download('a-bot', 124).on('pipe', write2stream)
