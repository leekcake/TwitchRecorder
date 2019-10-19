from twitch import TwitchClient, constants as tc_const
from recorder import Recorder

#Checker class
#It's check streams and

class Checker:
    client: TwitchClient = None
    id = None
    username = ""

    isLive = False
    recorder: Recorder = None

    def __init__(self, client, username):
        self.client = client
        self.username = username

    def update(self):
        if(self.id == None):
            self.id = self.client.users.translate_usernames_to_ids(self.username)[0]['id']

        if(self.isLive):
            try:
                stream = self.client.streams.get_stream_by_user(self.id, stream_type=tc_const.STREAM_TYPE_LIVE)
                if stream['broadcast_platform'] == tc_const.STREAM_TYPE_LIVE:
                    return
            except Exception:
                pass
            self.isLive = False
            self.recorder.intercept()
        else:
            try:
                stream = self.client.streams.get_stream_by_user(self.id, stream_type=tc_const.STREAM_TYPE_LIVE)
                if stream['broadcast_platform'] == tc_const.STREAM_TYPE_LIVE:
                    self.isLive = True
                    self.recorder = Recorder(self.username)
                    self.recorder.start()
            except Exception:
                pass

    def status(self) -> str:
        return "{}'s Broadcast: isLive {}".format(self.username, self.isLive)
