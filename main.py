from twitch import TwitchClient
from checker import Checker
import threading
from os import system, name


def clear():
    print(chr(27) + '[2j')
    print('\033c')
    print('\x1bc')
    # for windows
    if name == 'nt':
        _ = system('cls')

        # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')

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

        self.checkers.append(Checker(client, "pocari_on"))
        self.checkers.append(Checker(client, "lilac_unicorn_"))
        self.checkers.append(Checker(client, "dohwa_0904"))
        self.checkers.append(Checker(client, "wkgml"))
        self.update()

    def update(self):
        clear()
        print( "Updateing..." )
        for checker in self.checkers:
            checker.update()
        for checker in self.checkers:
            print(checker.status())
        threading.Timer(30, self.update).start()


if __name__ == "__main__":
    # execute only if run as a script
    Main().main()
