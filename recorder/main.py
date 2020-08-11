import glob
import time
from pathlib import Path

import requests
import streamlink
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile
from twitch import TwitchClient

import config
import provider
from checker import Checker
import threading
import os
from pydrive2.auth import GoogleAuth
import logging
import sys

import ntpath

# Main script :p


class Main:
    # Stream checkers in alive
    checkers = []
    # Twitch Client (Global)
    client: TwitchClient = None

    accessToken = ""

    noLive = 0

    inUpload = False
    thread = None
    drive = None
    rootDirId = None

    lastTotalSize = 0

    def main(self):
        # Configure logging module
        logging.basicConfig(filename='recorder.log', format='%(asctime)s %(message)s', filemode='a', level=logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        # logging.info("Twitch Recorder startup requested")
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

        self.drive = GoogleDrive(gauth)

        fd = open('rootDir.id', 'r')
        self.rootDirId = fd.readline()
        fd.close()

        self.refreshFetchList(True)
        threading.Timer(1, self.update).start()
        provider.launch(self)

    def refreshFetchList(self, isFirst):
        L = open("fetchList.txt", "r", encoding="utf-8").read().splitlines()
        dict = {}
        for line in L:
            if line.strip() == "" or line.strip().startswith('#'):
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
                print("Checking: " + checker.status())
                if checker.isLive:
                    self.noLive = 0
            except Exception:
                logging.exception("Failed to update checker of {}".format(checker.username))
                pass

        print("Check completed.")

        self.noLive += 1
        threading.Timer(30, self.update).start()

        grabbed = glob.glob(f'output/**/*.mp4', recursive=True)

        totalSize = 0
        for grab in grabbed:
            totalSize += os.path.getsize(grab)

        self.lastTotalSize = totalSize
        if totalSize > config.diskWarningQuota:
            if not os.path.exists('warning.flag'):
                logging.info(f"Storage Quota Warning")
                Path('warning.flag').touch()
                requests.get(f'https://maker.ifttt.com/trigger/upload_quota/with/key/{config.diskWarningIFTTT}')
            else:
                # Repeat Every 1 hour, hurry up!
                if os.stat('warning.flag').st_mtime < time.time() - 60 * 60:
                    logging.info(f"Storage Quota Re-Warning")
                    Path('warning.flag').touch()
                    requests.get(f'https://maker.ifttt.com/trigger/upload_quota/with/key/{config.diskWarningIFTTT}')
        else:
            if os.path.exists('warning.flag'):
                logging.info(f"Storage Quota Solved")
                os.remove('warning.flag')

        if totalSize > config.diskUploadQuota and not self.inUpload:
            finishList = glob.glob(f'output/**/Fin_*.mp4', recursive=True)
            if len(finishList) == 0:
                pass
            else:
                self.inUpload = True
                self.thread = threading.Thread(target=self.uploader, args=(finishList[0] + "",))
                self.thread.start()

    def uploader(self, path):
        try:
            spath = path.replace("\\", "/")
            spath = spath.replace("output/", "")

            split = spath.split("/")
            id = split[0]
            fn = split[1]

            logging.info(f"Upload Quota Upload Start: {fn} on {id}")
            folder: GoogleDriveFile = None

            folder_metadata = {'title': id,
                               'mimeType': 'application/vnd.google-apps.folder',
                               "parents": [{"kind": "drive#fileLink", "id": self.rootDirId}]}

            query = f"title = '{id}' and '{self.rootDirId}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.folder'"
            find = self.drive.ListFile({'q': query}).GetList()
            if len(find) != 0:
                folder = find[0]
            if folder is None:
                folder = self.drive.CreateFile(folder_metadata)
                folder.Upload()

            file = self.drive.CreateFile({'title': fn, "parents": [{"kind": "drive#fileLink", "id": folder['id']}]})
            file.SetContentFile(path)
            file.Upload()
            file.content.close()
            time.sleep(0.5) # Wait for release file by PyDrive2 / Anti-virus / etc
            os.remove(path)
            logging.info(f"Upload Quota Upload Finished: {path}")
        except Exception:
            logging.exception(f"Upload Quota Upload Failed: {path}")
        self.inUpload = False

if __name__ == "__main__":
    # execute only if run as a script
    Main().main()
