import logging
import threading
from io import BytesIO

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile

from storage.basestorage import BaseStorage


class Gdrive(BaseStorage):
    # Current chunk space
    memory = None
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

    def init(self):
        try:
            fd = open('rootDir.id', 'r')
            self.rootDirId = fd.readline()
            fd.close()
        except Exception:
            logging.warning("Recording without root directory?")

        self.gauth = GoogleAuth()
        self.gauth.LoadCredentialsFile("token.key")

        self.drive = GoogleDrive(self.gauth)

        folder_metadata = {'title': '{}_{}'.format(self.recorder.username, self.recorder.startedTime),
                           'mimeType': 'application/vnd.google-apps.folder',
                           "parents": [{"kind": "drive#fileLink", "id": self.rootDirId}]}
        folder = self.drive.CreateFile(folder_metadata)
        folder.Upload()
        self.myDir = folder

        self.myDirId = folder['id']

    def dispose(self):
        self.myDir['title'] = '{}_{}-Finished'.format(self.recorder.username, self.recorder.startedTime)
        self.myDir.Upload()

    def dropCurrentChunk(self):
        self.recorder.safeClose(self.memory)
        self.memory = BytesIO()
        self.currentSize = 0

    def flushCurrentChunk(self, waitFinish = False):
        if self.currentSize == 0:
            self.recorder.safeClose(self.memory)
            self.memory = BytesIO()
            logging.warning(
                '{}\'s Stream received request that flush chunk but current chunk size is 0, just recreate stream'.format(self.recorder.username))
            return
        if waitFinish:
            self.upload(self.recorder.currentPulse, self.currentInx, self.memory)
        else:
            threading.Thread(target=self.upload,
                             args=(self.recorder.currentPulse, self.currentInx, self.memory)).start()

        self.memory = BytesIO()
        self.currentInx += 1
        self.currentSize = 0

    # Helper method for get fn, for easier management of file name
    def getFNfromIndex(self, inx):
        return '{}_{}-{}.{}'.format(self.recorder.username, self.recorder.startedTime, self.recorder.currentPulse, inx)

    def startPush(self):
        self.currentInx = 0
        self.memory = BytesIO()

    def upload(self, pulse, inx, memory):
        try:
            memory.seek(0)
            logging.info("{}'s Recording: {}.{} chunk sending into drive".format(self.recorder.username, pulse, inx))
            file = self.drive.CreateFile({'title': self.getFNfromIndex(inx), "parents": [{"kind": "drive#fileLink", "id": self.myDirId}]})
            file.content = memory
            file.Upload()
            logging.info("{}'s Recording: {}.{} chunk sent into drive".format(self.recorder.username, pulse, inx))
        except Exception:
            logging.exception("{}'s Recording: failed to {}.{} chunk send into drive".format(self.recorder.username, pulse, inx))

        self.recorder.safeClose(memory)

    def push(self, data):
        self.memory.write(data)
        self.currentSize += len(data)

        if self.currentSize >= 1024 * 1024 * 100:
            self.flushCurrentChunk()

    def endPush(self):
        try:
            self.flushCurrentChunk(True)
        except Exception:
            pass