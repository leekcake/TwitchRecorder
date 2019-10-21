import streamlink
import threading
from datetime import datetime

from time import sleep

import os

from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth

import logging

from io import BytesIO

# Recorder class
# It's read stream and send to google drive


class Recorder:
    # Twitch username for record
    username = ""
    # Kill switch for fetcher
    fetcherKillSwitch = False

    # Current opened 'stream' for record 'twitch stream'
    stream = None

    # Current chunk space
    chunkMemory: BytesIO = None
    # Current chunk inx
    currentInx = 0
    # Current chunk's memory size
    currentSize = 0

    # Auth data for Google Drive
    gauth = None
    # Google drive classes for upload to google drive
    drive: GoogleDrive = None

    # Google drive folder id for cache root
    rootDirId = None
    # Google drive folder id for save cache
    myDirId = None

    # started time for set name of cache file
    startedTime = None

    # Flag for check fetcher's end. Is true when fetcher is started, and stopped working for some reasons
    isFetchFinished = False

    def __init__(self, _id):
        self.username = _id

    # Helper method for get fn, for easier management of file name
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

        self.openStream()  # Open twitch stream first for prevent empty google drive folder.
        # If stream is not alive, openStream will cause exception and prevent future codes and it's prevent google
        # folder creation

        self.gauth = GoogleAuth()
        self.gauth.LoadCredentialsFile("token.key")

        self.drive = GoogleDrive(self.gauth)

        folder_metadata = {'title': '{}_{}'.format(self.username, datetime.now().strftime("%Y%m%d_%H%M%S")), 'mimeType': 'application/vnd.google-apps.folder', "parents": [{"kind": "drive#fileLink", "id": self.rootDirId}]}
        folder = self.drive.CreateFile(folder_metadata)
        folder.Upload()

        self.myDirId = folder['id']

        logging.info("{}'s Stream detected, recorder startup!".format(self.username))
        threading.Thread(target=self.fetch).start()

    def openStream(self):
        streams = streamlink.streams("http://twitch.tv/{0}".format(self.username))
        stream = streams['best']
        self.stream = stream.open()

    def flushCurrentChunk(self):
        if self.currentSize == 0:
            logging.warning(
                '{}\'s Stream received request that flush chunk but current chunk size is 0, ignore request.')
            return
        threading.Thread(target=self.upload, args=(self.currentInx, self.chunkMemory)).start()
        self.chunkMemory = BytesIO()
        self.currentInx += 1
        self.currentSize = 0

    def fetch(self):
        logging.info("{}'s Recording fetch has been started".format(self.username))
        retry = 0
        self.chunkMemory = BytesIO()
        while not self.fetcherKillSwitch:
            try:
                if retry >= 10:
                    logging.info("{}'s Recording: Too many retries, may be end of stream, active kill switch".format(self.username))
                    self.fetcherKillSwitch = True
                    continue
                readed = self.stream.read(1024 * 256)

                if len(readed) == 0:
                    logging.warning("{}'s Recording: No more data, waiting for data. retry: {}".format(self.username, retry))
                    sleep(retry)
                    retry += 1
                    continue

                self.chunkMemory.write(readed)
                self.currentSize += len(readed)

                if self.currentSize >= 1024 * 1024 * 100:
                    self.flushCurrentChunk()

                retry = 0
            except IOError as io:
                try:
                    logging.exception("{}'s Recording: IOError detected, try to reset stream".format(self.username))
                    self.flushCurrentChunk()
                    self.openStream()
                except Exception:
                    logging.exception("{}'s Recording: Failed to Reset stream, active killSignal".format(self.username))
                    self.fetcherKillSwitch = True
                    pass
            except Exception as e:
                logging.exception("{}'s Recording: Exception caused, retry: {}".format(self.username, retry))
                sleep(retry)
                retry += 1
        try:
            self.flushCurrentChunk()
        except Exception:
            pass
        self.stream.close()
        self.isFetchFinished = True
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
        self.fetcherKillSwitch = True