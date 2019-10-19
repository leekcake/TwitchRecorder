from recorder import Recorder
from twitch import TwitchClient, constants as tc_const

# Checker class
# It's check streams and

import logging


class Checker:
    client: TwitchClient = None
    id = None
    username = ""
    isLive = False
    recorder: Recorder = None

    def __init__(self, client, username):
        self.client = client
        self.username = username

    def intercept(self):
        if self.recorder is not None:
            self.recorder.intercept()

    def update(self):
        if (self.id == None):
            logging.debug("Fetching id from username for {}".format(self.username))
            self.id = self.client.users.translate_usernames_to_ids(self.username)[0]['id']

        if (self.isLive):
            if self.recorder.isFinished:
                logging.warning(
                    "{}'s stream fetch finished but stream is still alive, try to restart recorder with reset live flag".format(
                        self.username))
                self.isLive = False
                # Recorder already finished so don't need to request intercept
                self.recorder = None
                return
            try:
                stream = self.client.streams.get_stream_by_user(self.id, stream_type=tc_const.STREAM_TYPE_LIVE)
                if stream['broadcast_platform'] == tc_const.STREAM_TYPE_LIVE:
                    return
            except Exception:
                pass
            logging.info("{}'s stream finished".format(self.username))
            self.isLive = False
            self.recorder.intercept()
            self.recorder = None
        else:
            try:
                stream = self.client.streams.get_stream_by_user(self.id, stream_type=tc_const.STREAM_TYPE_LIVE)
                if stream['broadcast_platform'] == tc_const.STREAM_TYPE_LIVE:
                    try:
                        logging.info("{}'s stream started".format(self.username))
                        self.isLive = True
                        self.recorder = Recorder(self.username)
                        self.recorder.start()
                    except Exception:
                        logging.error("Failed to start recorder for {}, reset checker for retry".format(self.username))
                        self.recorder = None
                        self.isLive = False
            except Exception:
                pass

    def status(self) -> str:
        return "{}'s Broadcast: isLive {} / Recording {}".format(self.username, self.isLive, self.recorder != None)
