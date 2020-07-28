import streamlink
import threading
from datetime import datetime

from time import sleep

import os

from pydrive2.drive import GoogleDrive
from pydrive2.auth import GoogleAuth

import logging

from io import BytesIO

# Recorder class
# It's read stream and send to google drive
from pydrive2.files import GoogleDriveFile
from streamlink import Streamlink

from config import outputTo, OUTPUT_GDRIVE, OUTPUT_DISK
from storage.basestorage import BaseStorage
from storage.disk import Disk
from storage.gdrive import Gdrive


class Recorder:
    # Twitch username for record
    username = ""
    # Kill switch for fetcher
    fetcherKillSwitch = False

    # Current opened 'stream' for record 'twitch stream'
    stream = None

    storage: BaseStorage

    # started time for set name of cache file
    startedTime = None

    # Flag for check fetcher's end. Is true when fetcher is started, and stopped working for some reasons
    isFetchFinished = False

    # Closed count, it's increased when recording is restarted because some state (exception, restart of stream, etc)
    # It's recorded and part of file name for notice recording status to user
    # In normal status, pulse don't increased!
    currentPulse = 0

    accessToken = ""

    def __init__(self, _id, accessToken):
        self.username = _id
        self.accessToken = accessToken

        if outputTo == OUTPUT_GDRIVE:
            self.storage = Gdrive()
        else:
            self.storage = Disk()
        self.storage.recorder = self

    def newPulse(self):
        self.currentPulse += 1
        logging.warning("{}'s Stream started {} pulse".format(self.username, self.currentPulse))

    def start(self):
        self.startedTime = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.openStream()  # Open twitch stream first for prevent empty google drive folder.
        # If stream is not alive, openStream will cause exception and prevent future codes and it's prevent google
        # folder creation

        self.storage.init()

        logging.info("{}'s Stream detected, recorder startup!".format(self.username))
        threading.Thread(target=self.fetch).start()

    def openStream(self):
        self.safeClose(self.stream)
        session = Streamlink()
        if self.accessToken != "":
            session.set_plugin_option('twitch', 'oauth-token', self.accessToken)
        streams = streamlink.streams("http://twitch.tv/{0}".format(self.username))
        stream = streams['best']
        self.stream = stream.open()

    def safeClose(self, io):
        try:
            if io is not None:
                io.close()
        except Exception:
            logging.exception("Safe close failed")
            pass

    def dispose(self):
        self.intercept()
        while not self.isFetchFinished:
            sleep(0.2)

        self.storage.dispose()

    def recoverFetcher(self):
        if self.isFetchFinished is not True:
            logging.warning("{}'s Stream received request that recover fetcher but fetcher is alive?".format(self.username))
            return
        # If fetcher is finished, chunk already flushed :)
        self.openStream()
        self.fetcherKillSwitch = False
        self.isFetchFinished = False
        self.newPulse()
        threading.Thread(target=self.fetch).start()

    def fetch(self):
        logging.info("{}'s Recording fetch has been started".format(self.username))
        waitCount = 0
        recoverTries = 0
        killByError = False

        self.storage.startPush()

        while not self.fetcherKillSwitch:
            try:
                if recoverTries >= 10:
                    logging.info("{}'s Recording: Too many retires, may be end of stream, active kill switch".format(self.username))
                    self.fetcherKillSwitch = True
                    continue
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

                self.storage.push(readed)

                waitCount = 0
                recoverTries = 0
            except IOError as io:
                    logging.exception("{}'s Recording: IOError detected, may be end of stream, active kill switch".format(self.username))
                    self.fetcherKillSwitch = True
                    killByError = True
                    continue
            except Exception as e:
                    logging.exception("{}'s Recording: Exception detected, may be end of stream, active kill switch".format(self.username))
                    self.fetcherKillSwitch = True
                    killByError = True
                    continue

        self.storage.endPush()
        self.safeClose(self.stream)

        self.isFetchFinished = True
        logging.info("{}'s Stream Fetch has been finished".format(self.username))

    def intercept(self):
        self.fetcherKillSwitch = True