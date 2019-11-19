import streamlink
from twitch import TwitchClient
from checker import Checker
import threading
import os
from pydrive.auth import GoogleAuth
import logging
import sys

# Main script :p


class Main:
    # Stream checkers in alive
    checkers = []
    # Twitch Client (Global)
    client: TwitchClient = None

    accessToken = ""

    noLive = 0

    def main(self):
        # Configure logging module
        logging.basicConfig(filename='recorder.log', format='%(asctime)s %(message)s', filemode='a', level=logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.info("Twitch Recorder startup requested")
        logging.getLogger('googleapiclient.discovery_cache').setLevel(
            logging.ERROR)  # Mute discovery warning, it's working baby
        logging.getLogger('streamlink.stream.hls').setLevel(
            logging.ERROR)  # TODO: Mute Failed to reload playlist, I don't have idea deal with it.

        logging.debug("Check Twitch API")

        f = open('twitch.token', 'r')
        clientId = f.readline()
        oAuthToken = ""
        if (f.readable()):
            oAuthToken = f.readline()
        f.close()

        self.client = TwitchClient(client_id=clientId, oauth_token=oAuthToken)

        logging.debug("Check Twitch Token")
        if os.path.exists('twitch_access.token'):
            f = open('twitch_access.token', 'r')
            self.accessToken = f.readline()
            f.close()

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
        logging.info("{} streamers registered for record, start TwitchRecorder-GoogleDrive".format(len(self.checkers)))
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
                checker.dispose()
                self.checkers.remove(checker)
            else:
                del dict[checker.username]

        for username in dict.keys():
            if not isFirst:
                logging.info("{} added to list, check/record will started".format(username))
            self.checkers.append(Checker(self.client, username, self.accessToken))

    def update(self):
        if os.path.exists("refreshFetchList.flag"):
            try:
                logging.info("FetchList refresh flag detected! refresh")
                self.refreshFetchList(False)
            except Exception:
                logging.exception("Failed to reload fetch list :(")
                pass
            os.remove("refreshFetchList.flag")

        for checker in self.checkers:
            try:
                checker.update()
                if checker.isLive:
                    self.noLive = 0
            except Exception:
                logging.exception("Failed to update checker of {}".format(checker.username))
                pass
        for checker in self.checkers:
            print(checker.status())

        self.noLive += 1
        if self.noLive <= 3:
            threading.Timer(30, self.update).start()
        else:
            logging.info("No live channel in 1min 30 seconds, restart...")
            sys.exit(1)


if __name__ == "__main__":
    # execute only if run as a script
    Main().main()
