import os
import threading
import time
from typing.io import BinaryIO

from storage.basestorage import BaseStorage


class Disk(BaseStorage):
    disk: BinaryIO
    memory: list
    lock: threading.Lock
    thread: threading.Thread = None
    uploaderIsLive = False
    intercept = False

    def init(self):
        pass

    def dispose(self):
        pass

    def getFN(self):
        return '{}_{}-{}.{}'.format(self.recorder.username, self.recorder.startedTime, self.recorder.currentPulse,
                                    'mp4')

    def startPush(self):
        if not os.path.exists("output"):
            os.mkdir("output")
        if not os.path.exists("output/" + self.recorder.username):
            os.mkdir("output/" + self.recorder.username)
        self.disk = open(f'output/{self.recorder.username}/' + self.getFN(), 'wb')
        self.memory = []
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.uploader, args=(self.disk, self.memory, self.lock))
        self.thread.start()

    def push(self, data):
        self.lock.acquire()
        self.memory.append(data)
        self.lock.release()

    def endPush(self):
        self.intercept = True
        while self.uploaderIsLive:
            time.sleep(0.2)

        self.disk.close()
        input = f'output/{self.recorder.username}/' + self.getFN()
        if os.path.getsize(input) == 0:
            os.remove(f'output/{self.recorder.username}/' + self.getFN())
        else:
            os.rename(f'output/{self.recorder.username}/' + self.getFN(),
                      f'output/{self.recorder.username}/' + "Fin_" + self.getFN())

    def uploader(self, disk, memory, lock):
        self.uploaderIsLive = True
        while True:
            lock.acquire()
            data = None
            if len(memory) != 0:
                data = memory[0]
                del memory[0]
            lock.release()
            if data is None:
                if self.recorder.isFetchFinished or self.intercept:
                    break
                time.sleep(1)
            else:
                disk.write(data)
                disk.flush()
        self.uploaderIsLive = False
