#################
# Basic example #
#################

import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from index import xdcc  # noqa


# MINIMAL SETUP :
xdccPY = xdcc('irc.server.net', path='downloads', verbose=True)

# STARTING DOWNLOAD(S) :
xdccPY.download('a-bot', 102)
