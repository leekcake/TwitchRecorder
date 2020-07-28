class BaseStorage:
    recorder = None

    def init(self):
        pass

    def dispose(self):
        pass

    def startPush(self):
        pass

    def push(self, data):
        pass

    def endPush(self):
        pass