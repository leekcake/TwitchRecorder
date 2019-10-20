# TwitchRecorder-GoogleDrive
Record twitch stream into google drive, without using local disk

## Purpose of development
2019년 9월에 트위치 스트리밍을 보기 시작했습니다.
어느날 다시보기를 하려고 하자 어떤 다시보기는 사라져 있었고
어떤 다시보기는 일부가 음소거 되어 있었습니다.

다시보기가 사라지는것은 TwitchLeecher를 쓰면 되긴 했지만, 음소거되어 버린건 어쩔수가 없었던것도 있고, 스트리머가 다운로드 받기 전에 지우는 경우도 있었습니다.
그래서 고민하다가 놀고 있는 Odroid-XU4를 통해 방송을 받기로 했고. 그래서 구현이 되었습니다.
이 프로그램이 디스크 대신 메모리와 구글 드라이브를 사용하는것도 Odroid-XU4에서 굴러가야 되기 때문입니다. 16GB SD카드로는 전체 방송을 저장한뒤 업로드 하는것은 무리였습니다. 나중에 따로 합치더라도 일단 원본을 구해두는게 좋다는 취지에서, 개발되었습니다.

In 2019/9, I started watch twitch streaming.
someday I tried to watch replay, some replay was removed
and some replay muted audio for some parts

Replay that removed by time limit can be solved with TwitchLeecher, but muted audio and streamer delete video before time limit not solved.
So I searching for solution, and I decided the mind to use Odroid-XU4(Idle in my room) for download stream, So I developed this.
It's reason that use mem/google drive instead of local disk. 16GB SD Card not enough to store 2GB~10GB streams, also sd is slooooow for handle many channel.
So It's save stream chunk into mem(100MB), and send it google drive.

## Typical checklist
- If streamer end stream and hosting somebody immediately, this program also record hosting stream. it closed within 3 minute.
- This program is not tested for record too long time / download many streamer in same time.
- This program cause some error on high workload / linux server? still in testing for it.
--([('system library', 'fopen', 'Too many open files'), ('BIO routines', 'BIO_new_file', 'system lib'), ('x509 certificate routines', 'X509_load_cert_crl_file', 'system lib')])
- I do not guarantee that this will work normally.
-   Because my English is not good, overall word selection and long sentence completion may be inadequate.
## How to launch this program

 - Install python3
 - Download project
 - Open cmd / sh / bash / etc in project folder
 - pip freeze > requirements.txt
 - make twitch.token like below, How? [Here](https://dev.twitch.tv/docs/authentication/)

> [YOUR-TWITCH-TOKEN]

 - make FetchList.txt like below

> streamer_id - Some memo on here
> <br>Ex)
> <br>lilac_unicorn_ - 닉혼곤듀
> <br>dohwa_0904 - 도화(여왕)님_
> <br>nopetori - 귀여운 노페토리님
 -
 - make client_secrets.json, How? [Here](https://pythonhosted.org/PyDrive/quickstart.html#authentication)
 - make rootDir.id like below, is Option but recommended, Where to get? [Here](https://ploi.io/documentation/mysql/where-do-i-get-google-drive-folder-id)
 >
> [YOUR-DRIVE-FOLDER-ID]
 - python main.py
 - ...?
 - PROFIT!
