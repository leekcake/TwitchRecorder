from twitch import TwitchClient
from checker import Checker
import threading

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive']


# Main script :p
class Main:
    checkers = []

    def main(self):
        print("Twitch Recorder with Google Drive")

        print("Check Twitch API")

        f = open('twitch.token', 'r')
        clientId = f.readline()
        oAuthToken = ""
        if (f.readable()):
            oAuthToken = f.readline()
        f.close()

        client = TwitchClient(client_id=clientId, oauth_token=oAuthToken)

        print("Check Google Drive API")
        """Shows basic usage of the Drive v3 API.
        Prints the names and ids of the first 10 files the user has access to.
        """
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

        self.checkers.append(Checker(client, "pocari_on"))
        self.checkers.append(Checker(client, "lilac_unicorn_"))
        self.checkers.append(Checker(client, "dohwa_0904"))
        self.checkers.append(Checker(client, "wkgml"))
        self.update()

    def update(self):
        for checker in self.checkers:
            checker.update()
            print(checker.status())

        threading.Timer(30, self.update).start()


if __name__ == "__main__":
    # execute only if run as a script
    Main().main()
