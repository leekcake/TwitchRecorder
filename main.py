from twitch import TwitchClient

from checker import Checker
import threading
from os import system, name
import os
from pydrive.auth import GoogleAuth

import logging
import sys

def clear():
    return
    # for windows
    if name == 'nt':
        _ = system('cls')

        # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')

    # Main script :p


class Main:
    checkers = []
    client: TwitchClient = None

    def main(self):
        logging.basicConfig(filename='recorder.log', format='%(asctime)s %(message)s', filemode='w', level=logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.info("Twitch Recorder startup requested")
        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR) # Mute discovery warning, it's working baby

        logging.debug("Check Twitch API")

        f = open('twitch.token', 'r')
        clientId = f.readline()
        oAuthToken = ""
        if (f.readable()):
            oAuthToken = f.readline()
        f.close()

        self.client = TwitchClient(client_id=clientId, oauth_token=oAuthToken)

        logging.debug("Check Google Drive API")
        gauth = GoogleAuth()
        gauth.settings['get_refresh_token'] = True
        # Create local webserver and auto handles authentication.
        gauth.LoadCredentialsFile("token.key")
        if gauth.credentials is None:
            # Authenticate if they're not there
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            # Refresh them if expired
            gauth.Refresh()
        else:
            # Initialize the saved creds
            gauth.Authorize()
        # Save the current credentials to a file
        gauth.SaveCredentialsFile("token.key")

        self.refreshFetchList(True)
        logging.info("{} streamers loaded, start TwitchRecorder-GoogleDrive".format(len(self.checkers)))
        self.update()

    def refreshFetchList(self, isFirst):
        L = open("fetchList.txt", "r", encoding="utf-8").read().splitlines()
        dict = {}
        for line in L:
            if line.strip() == "":
                continue
            line = line.split("-")[0].strip()
            dict[line] = "Yes"

        for checker in self.checkers:
            if not checker.username in dict:
                logging.info("{} removed from list, cleanup will started".format(checker.username))
                checker.intercept()
                del self.checkers[checker.username]
            else:
                del dict[checker.username]

        for username in dict.keys():
            if not isFirst:
                logging.info("{} added to list, check/record will started".format(username))
            self.checkers.append(Checker(self.client, username))

    def update(self):
        if os.path.exists("refreshFetchList.flag"):
            logging.info("FetchList refresh flag detected! refresh")
            self.refreshFetchList(False)
            os.remove("refreshFetchList.flag")

        for checker in self.checkers:
            checker.update()
        for checker in self.checkers:
            print(checker.status())
        threading.Timer(30, self.update).start()


if __name__ == "__main__":
    # execute only if run as a script
    Main().main()
