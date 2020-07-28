from recorder import Recorder
from twitch import TwitchClient, constants as tc_const

# Checker class
# It's check streams and

import logging


class Checker:
    # Twitch client from main.py
    client: TwitchClient = None
    # Twitch user id for check
    id = None
    # Twitch user name for check
    username = ""
    # Live status of Twitch streamer
    isLive = False
    # Current activated recorder
    recorder: Recorder = None

    accessToken = ""

    def __init__(self, client, username, accessToken):
        self.client = client
        self.username = username
        self.accessToken = accessToken

    def dispose(self):
        if self.recorder is not None:
            self.recorder.intercept()

    def update(self):
        if self.id is None:
            logging.debug("Fetching twitch id from username for {}".format(self.username))
            self.id = self.client.users.translate_usernames_to_ids(self.username)[0]['id']

        if self.isLive:
            try:
                stream = self.client.streams.get_stream_by_user(self.id, stream_type=tc_const.STREAM_TYPE_LIVE)
                if stream['broadcast_platform'] == tc_const.STREAM_TYPE_LIVE:
                    # If streaming is live, we need to check recorder finish for revive dead recorder if dead
                    if self.recorder.isFetchFinished:
                        print(stream)
                        logging.warning(
                            "{}'s stream fetch finished but stream is still alive, try to recover fetcher".format(
                                self.username))
                        try:
                            self.recorder.recoverFetcher()
                        except Exception:
                            pass
                    return
            except Exception:
                pass
            # If stream is offline, stop recorder
            logging.info("{}'s stream finished".format(self.username))
            self.isLive = False
            self.recorder.dispose()
            self.recorder = None
        else:
            try:
                # If stream is alive, start recorder!
                stream = self.client.streams.get_stream_by_user(self.id, stream_type=tc_const.STREAM_TYPE_LIVE)
                if stream['broadcast_platform'] == tc_const.STREAM_TYPE_LIVE:
                    try:
                        logging.info("{}'s stream started".format(self.username))
                        self.isLive = True
                        self.recorder = Recorder(self.username, self.accessToken)
                        self.recorder.start()
                    except Exception:
                        # If failed to start recorder but stream seen alive, reset live flag for retry!
                        logging.exception("Failed to start recorder for {}, reset checker for retry".format(self.username))
                        self.recorder = None
                        self.isLive = False
            except Exception:
                pass

    def status(self) -> str:
        return "{}'s Broadcast: isLive {} / Recording {}".format(self.username, self.isLive, self.recorder != None)
