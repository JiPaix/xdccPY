################################
# Example showing all features #
################################

import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from index import xdcc  # noqa


# Except for the irc server all options are optionnal
xdccPY = xdcc(
    'irc.server.net',               # IRC server
    path='downloads',               # Download path (default: None) [!] having no path enables piping [!]
    nick='ItsMeJiPaix',             # Nickname on IRC (default: 'xdccPY')
    randomize_nick=False,           # Add random numbers to nickname (default: True)
    chan=['candies', 'fruits'],     # IRC channel(s) to join (default: None)
    retry=5,                        # Number of retries before skipping pack (default: 1)
    passive_port=5555,              # Port to use with passive DCC (default: 5001)
    wait=2,                         # Number of seconds to wait before sending xdcc requests (default: 0)
    verbose=True                    # Display download information/progress/errors (default: False)
)

# HOW TO DOWNLOAD :
xdccPY.download('a-bot', 102)  # Start Job1
xdccPY.download('another-bot', 320)  # Start Job2
xdccPY.download('a-bot', '130-133')  # Update Job1


# HOW TO USE EVENTS :

job = xdccPY.download('any-bot', '255-260')  # store a job in a variable

# prepare function to handle events
def when_downloaded(*args):
    for arg in args:
        print(arg)

def when_error(*args):
    for arg in args:
        print(arg)

# usage :
job.on('downloaded', when_downloaded)  # will print a dict with file information
job.on('error', when_error)  # will print an error message and a dict with file information
