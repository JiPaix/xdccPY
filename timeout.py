import threading
import asyncio


class TimeOut():
    def __init__(self):
        self.timer = None

    def start(
            self,
            delay,
            function,
            message,
            streams,
            padding=0):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(
            delay,
            thr,
            kwargs={
                'fn': function,
                'msg': message,
                'streams': streams,
                'padding': padding
            })
        self.timer.start()

    def stop(self):
        if self.timer:
            if self.timer.is_alive():
                self.timer.cancel()

    def join(self):
        if self.timer:
            if self.timer.is_alive():
                self.timer.join()


def thr(**kwargs):
    fn = kwargs["fn"]
    msg = kwargs["msg"]
    stream = kwargs["streams"]
    padding = kwargs["padding"]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(fn(msg, stream, padding))
    loop.close()
