from recorder import Recorder

# Checker class
# It's check streams and

import logging


class Checker:
    username = ""
    recorder: Recorder = None

    def __init__(self, username):
        self.username = username

    def intercept(self):
        if self.recorder is not None:
            self.recorder.intercept()

    def update(self):
        if self.recorder != None:
            if self.recorder.isFinished:
                logging.info(
                    "{}'s stream finished!".format(
                        self.username))
                self.recorder = None
                return
        else:
            try:
                self.recorder = Recorder(self.username)
                self.recorder.start()
            except Exception:
                self.recorder = None

    def status(self) -> str:
        return "{}'s Broadcast: Recording {}".format(self.username, self.recorder != None)
