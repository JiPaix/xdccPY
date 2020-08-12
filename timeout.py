import threading


class TimeOut():
    def __init__(self):
        self.timer = None

    def start(self, delay, function, *args, **kwargs):
        if self.timer:
            self.stop()
        self.timer = threading.Timer(delay, function, args=args, kwargs=kwargs)
        self.timer.start()

    def stop(self):
        if self.timer:
            if self.timer.is_alive():
                self.timer.cancel()
