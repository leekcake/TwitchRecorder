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
        if (self.id == None):
            logging.debug("Fetching id from username for {}".format(self.username))
            self.id = self.client.users.translate_usernames_to_ids(self.username)[0]['id']

        if self.recorder != None:
            if self.recorder.isFinished:
                logging.warning(
                    "{}'s stream fetch finished! reset checker for live check".format(
                        self.username))
                # Recorder already finished so don't need to request intercept
                self.recorder = None
                return
        else:
            try:
                self.recorder = Recorder(self.username)
            except Exception:
                self.recorder = None

    def status(self) -> str:
        return "{}'s Broadcast: Recording {}".format(self.username, self.recorder != None)
