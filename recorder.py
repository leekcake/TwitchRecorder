import streamlink
import threading
from datetime import datetime

from time import sleep

import os

from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth

import logging

from io import BytesIO

#Recorder class
#It's read stream and send to google drive

class Recorder:
    username = ""
    killSignal = False
    stream = None

    currentInx = 0
    currentSize = 0

    gauth = None
    drive:GoogleDrive = None

    rootDirId = None
    myDirId = None

    startedTime = None

    isFinished = False

    def __init__(self, _id):
        self.username = _id

    def getFNfromIndex(self, inx):
        return '{}_{}.{}'.format(self.username, self.startedTime, inx)

    def start(self):
        self.startedTime = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            fd = open('rootDir.id', 'r')
            self.rootDirId = fd.readline()
            fd.close()
        except Exception:
            logging.warning("Recording without root directory?")

        streams = streamlink.streams("http://twitch.tv/{0}".format(self.username))
        stream = streams['best']
        self.stream = stream.open()

        self.gauth = GoogleAuth()
        # Create local webserver and auto handles authentication.
        self.gauth.LoadCredentialsFile("token.key")

        self.drive = GoogleDrive(self.gauth)

        folder_metadata = {'title': '{}_{}'.format(self.username, datetime.now().strftime("%Y%m%d_%H%M%S")), 'mimeType': 'application/vnd.google-apps.folder', "parents": [{"kind": "drive#fileLink", "id": self.rootDirId}]}
        folder = self.drive.CreateFile(folder_metadata)
        folder.Upload()

        self.myDirId = folder['id']

        logging.info("{}'s Stream detected, recorder startup!".format(self.username))
        threading.Thread(target=self.fetch).start()

    def fetch(self):
        logging.info("{}'s Stream Fetch has been started".format(self.username))
        retry = 0
        memory = BytesIO()
        while not self.killSignal:
            try:
                if retry >= 10:
                    logging.info("{}'s Stream: Too many retries, may be end of stream, active killSignal".format(self.username))
                    self.killSignal = True
                    continue
                readed = self.stream.read(1024 * 256)

                if len(readed) == 0:
                    logging.warning("{}'s Stream: No more data, waiting for data. retry: {}".format(self.username, retry))
                    sleep(retry)
                    retry += 1
                    continue

                memory.write(readed)
                self.currentSize += len(readed)

                if self.currentSize >= 1024 * 1024 * 100:
                    threading.Thread(target=self.upload, args=(self.currentInx,memory)).start()
                    memory = BytesIO()
                    self.currentInx += 1
                    self.currentSize = 0

                retry = 0
            except Exception:
                logging.error("Exception in Fetching of {}, retry: {}".format(self.username, retry))
                sleep(retry)
                retry += 1
        try:
            self.upload(self.currentInx, memory)
        except Exception:
            pass
        self.stream.close()
        self.isFinished = True
        logging.info("{}'s Stream Fetch has been finished".format(self.username))

    def upload(self, inx, memory):
        memory.seek(0)
        logging.info("{}'s Recording: {} chunk sending into drive".format(self.username, inx))
        file = self.drive.CreateFile({'title': self.getFNfromIndex(inx), "parents": [{"kind": "drive#fileLink", "id": self.myDirId}]})
        file.content = memory
        file.Upload()
        memory.close()
        logging.info("{}'s Recording: {} chunk sent into drive".format(self.username, inx))

    def intercept(self):
        self.killSignal = True