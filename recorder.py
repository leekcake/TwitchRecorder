import streamlink
import threading
from datetime import date
import queue
from time import sleep

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

#Recorder class
#It's read stream and send to google drive

class Recorder:
    id = ""
    killSignal = False
    stream = None

    localStream = None
    creds = None

    received:queue.Queue = queue.Queue()

    def __init__(self, _id):
        self.id = _id

    def start(self):
        print("{}'s Record requested!".format(self.id))
        #with open('token.pickle', 'rb') as token:
        #    creds = pickle.load(token)

        streams = streamlink.streams("http://twitch.tv/{0}".format(self.id))
        stream = streams['best']
        self.stream = stream.open()
        self.localStream = open('{}_{}.dat'.format(self.id, date.today().strftime("%Y%m%d_%H%M%S")), 'wb')

        threading.Thread(target=self.fetch).start()
        threading.Thread(target=self.save).start()

    def fetch(self):
        print("{}'s Fetch started!".format(self.id))
        while not self.killSignal:
            if(self.received.qsize() >= (1024 * 16)): #Wait for Upload / Write
                sleep(1)
                continue
            try:
                self.received.put( self.stream.read(1024) )
            except Exception:
                self.killSignal = True

        print("{}'s Fetch finished!".format(self.id))

    def save(self):
        print("{}'s Save started!".format(self.id))
        while not self.killSignal or self.received.qsize() != 0:
            if self.received.qsize() != 0:
                data = self.received.get()
                self.localStream.write(data)

        print("{}'s Save finished!".format(self.id))

    def intercept(self):
        print("{}'s Record intercepted!".format(self.id))
        self.killSignal = True