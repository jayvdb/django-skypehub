from select import select
from socket import socketpair
from time import time
from struct import pack, unpack

from skypehub.models import Message

def message_logging_receiver(handler, message, status):
    Message.objects.create(
        body=message.Body,
        sender=message.Sender.Handle,
        chat_name=message.Chat.Name,
    )

class OnMessageHandler(object):
    """
    Skype OnMessage event handler
    """
    default_statuses = ('RECEIVED',)
    default_receivers = ()

    def __init__(self, skype=None):
        self.receivers = list(self.default_receivers)
        self.skype = skype

    def connect(self, receiver, statuses=None):
        if statuses is None:
            statuses = list(self.default_statuses)
        if not receiver in self.receivers:
            self.receivers.append((statuses, receiver))

    def dispatch(self, message, status):
        for statuses, receiver in self.receivers:
            if status in statuses:
                receiver(self, message, status)

class OnTimeHandler(object):
    """
    Skype OnTime event handler
    by moriyoshi
    """
    def __init__(self, skype=None):
        self.skype = skype
        self.pair = socketpair()
        self.timepoints = []
        self.callables = {}
        self._callables = {}
        self.id = 1

    def connect(self, callable, time):
        id = self.callables.get(callable, 0)
        if not id:
            id = self.id
            self.id += 1
            self.callables[callable] = id
            self._callables[id] = callable
        self.pair[1].send(pack("@ii", time, id))

    def __call__(self):
        wait = None
        while True:
            r, w, e = select([self.pair[0]], [], [], wait)
            if r:
                t, id = unpack("@ii", r[0].recv(8))
                i = self.search_nearest(t)
                self.timepoints.insert(i, (t, id))
                wait = max(self.timepoints[0][0] - time(), 0)
            else:
                _time, id = self.timepoints.pop(0)
                self._callables[id](self, _time)
                if self.timepoints:
                    wait = max(self.timepoints[0][0] - time(), 0)
                else:
                    wait = None

    def search_nearest(self, time):
        l = len(self.timepoints)
        if l == 0:
            return 0
        s = 0
        e = l

        while True:
            i = (s + e) // 2
            if self.timepoints[i][0] < time:
                s = i
                i = (i + e) // 2
                if i == l - 1:
                    i = l
                    break
            else:
                e = i
                i = (s + i) // 2
                if i == 0:
                    break
        return i


on_message = OnMessageHandler()
on_time = OnTimeHandler()
on_message.connect(message_logging_receiver)