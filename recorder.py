import streamlink
import threading
from datetime import datetime

#Recorder class
#It's read stream and send to google drive

class Recorder:
    id = ""
    killSignal = False
    stream = None

    localStream = None

    def __init__(self, _id):
        self.id = _id

    def start(self):
        streams = streamlink.streams("http://twitch.tv/{0}".format(self.id))
        stream = streams['best']
        self.stream = stream.open()
        self.localStream = open('{}_{}.dat'.format(self.id, datetime.now().strftime("%Y%m%d_%H%M%S")), 'wb')

        threading.Thread(target=self.fetch).start()

    def fetch(self):
        while not self.killSignal:
            try:
                self.localStream.write( self.stream.read(1024 * 256) )
            except Exception:
                self.killSignal = True

    def intercept(self):
        self.killSignal = True