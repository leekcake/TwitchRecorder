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
from pydrive.files import GoogleDriveFile


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
    myDir: GoogleDriveFile = None
    myDirId = None

    # started time for set name of cache file
    startedTime = None

    # Flag for check fetcher's end. Is true when fetcher is started, and stopped working for some reasons
    isFetchFinished = False

    # Closed count, it's increased when recording is restarted because some state (exception, restart of stream, etc)
    # It's recorded and part of file name for notice recording status to user
    # In normal status, pulse don't increased!
    currentPulse = 0

    def __init__(self, _id):
        self.username = _id

    def newPulse(self):
        self.currentPulse += 1
        self.currentInx = 0

    # Helper method for get fn, for easier management of file name
    def getFNfromIndex(self, inx):
        return '{}_{}-{}.{}'.format(self.username, self.startedTime, self.currentPulse, inx)

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

        folder_metadata = {'title': '{}_{}'.format(self.username, self.startedTime), 'mimeType': 'application/vnd.google-apps.folder', "parents": [{"kind": "drive#fileLink", "id": self.rootDirId}]}
        folder = self.drive.CreateFile(folder_metadata)
        folder.Upload()
        self.myDir = folder

        self.myDirId = folder['id']

        logging.info("{}'s Stream detected, recorder startup!".format(self.username))
        threading.Thread(target=self.fetch).start()

    def openStream(self):
        streams = streamlink.streams("http://twitch.tv/{0}".format(self.username))
        stream = streams['best']
        self.stream = stream.open()

    def flushCurrentChunk(self, waitFinish = False):
        if self.currentSize == 0:
            logging.warning(
                '{}\'s Stream received request that flush chunk but current chunk size is 0, ignore request.')
            return
        if waitFinish:
            threading.Thread(target=self.upload, args=(self.currentPulse, self.currentInx, self.chunkMemory)).start()
        else:
            self.upload(self.currentPulse, self.currentInx, self.chunkMemory)
        self.chunkMemory = BytesIO()
        self.currentInx += 1
        self.currentSize = 0

    def dispose(self):
        self.intercept()
        while not self.isFetchFinished:
            sleep(0.2)

        self.myDir['title'] = '{}_{}-Finished'.format(self.username, self.startedTime)

    def recoverFetcher(self):
        if self.isFetchFinished is not True:
            logging.warning("{}'s Stream received request that recover fetcher but fetcher is alive?")
            return
        # If fetcher is finished, chunk already flushed :)
        self.openStream()
        self.fetcherKillSwitch = False
        threading.Thread(target=self.fetch).start()

    def fetch(self):
        logging.info("{}'s Recording fetch has been started".format(self.username))
        waitCount = 0
        self.chunkMemory = BytesIO()
        while not self.fetcherKillSwitch:
            try:
                if waitCount >= 10:
                    logging.info("{}'s Recording: Too many wait, may be end of stream, active kill switch".format(self.username))
                    self.fetcherKillSwitch = True
                    continue
                readed = self.stream.read(1024 * 256)

                if len(readed) == 0:
                    logging.warning("{}'s Recording: No more data, waiting for data. retry: {}".format(self.username, waitCount))
                    sleep(0.5)
                    waitCount += 1
                    continue

                self.chunkMemory.write(readed)
                self.currentSize += len(readed)

                if self.currentSize >= 1024 * 1024 * 100:
                    self.flushCurrentChunk()

                waitCount = 0
            except IOError as io:
                try:
                    logging.exception("{}'s Recording: IOError detected, try to reset stream".format(self.username))
                    self.flushCurrentChunk(True)
                    self.openStream()
                    self.newPulse()
                except Exception:
                    logging.exception("{}'s Recording: Failed to Reset stream, active killSignal".format(self.username))
                    self.fetcherKillSwitch = True
                    pass
            except Exception as e:
                try:
                    logging.exception("{}'s Recording: Exception detected, try to reset stream".format(self.username))
                    self.flushCurrentChunk(True)
                    self.openStream()
                    self.newPulse()
                except Exception:
                    logging.exception("{}'s Recording: Failed to Reset stream, active killSignal".format(self.username))
                    self.fetcherKillSwitch = True
                    pass
        try:
            self.flushCurrentChunk(True)
        except Exception:
            pass
        try:
            self.stream.close()
        except IOError:
            pass

        self.isFetchFinished = True
        logging.info("{}'s Stream Fetch has been finished".format(self.username))

    def upload(self, pulse, inx, memory):
        memory.seek(0)
        logging.info("{}'s Recording: {}.{} chunk sending into drive".format(self.username, pulse, inx))
        file = self.drive.CreateFile({'title': self.getFNfromIndex(inx), "parents": [{"kind": "drive#fileLink", "id": self.myDirId}]})
        file.content = memory
        file.Upload()
        memory.close()
        logging.info("{}'s Recording: {}.{} chunk sent into drive".format(self.username, pulse, inx))

    def intercept(self):
        self.fetcherKillSwitch = True