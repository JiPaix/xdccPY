from typing import Any, Dict, Union, Iterable, List


class Job():
    def __init__(self, bot: str, packages: List[int]):
        self.id = bot
        self.queue = packages
        self.done: List[str] = []
        self.failed: List[int] = []
        self.source: Union[str] = ''
        self.now: int = 0
        self.callbacks = None

    def is_done(self):
        if len(self.done) == len(self.queue):
            return True
        elif len(self.done) + len(self.failed) == len(self.queue):
            return True
        else:
            return False

    def on(self, event_name, callback):
        if self.callbacks is None:
            self.callbacks = {}

        if event_name not in self.callbacks:
            self.callbacks[event_name] = [callback]
        else:
            self.callbacks[event_name].append(callback)

    def trigger(self, event_name, *data):
        if self.callbacks is not None and event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                callback(*data)

    def show(self):
        """returns current Job values in a dict
        """
        return dict(
            id=self.id,
            queue=self.queue,
            done=self.done,
            failed=self.failed)
