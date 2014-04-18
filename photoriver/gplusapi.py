import requests

from xml.etree import ElementTree

import logging
logger = logging.getLogger(__name__)

auth_url = "https://accounts.google.com/o/oauth2/auth"
client_id = "834388343680-embh8gpuiavu35801g2564sfrkir3rfb.apps.googleusercontent.com"
client_secret = "jMX0btH5hLlfJgxXF6-bUgf6"
redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
token_uri = "https://accounts.google.com/o/oauth2/token"

url_base = "https://picasaweb.google.com/data/"
url_albums = "https://picasaweb.google.com/data/feed/api/user/default"


class GPhoto(object):
    def __init__(self, username):
        url = "{}?client_id={}&redirect_uri={}&scope={}&response_type=code".format(auth_url, client_id, redirect_uri, url_base)
        logger.warning("Authentication URL: %s", url)
        code = input("Paste authorization code: ")
        token_json = requests.post(
            token_uri,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": 'urn:ietf:wg:oauth:2.0:oob',
                "grant_type": "authorization_code",
            },
        ).json()
        self.token = token_json["access_token"]
        self.headers = {
            "Authorization": "Bearer {}".format(self.token)
        }

    def get_albums(self):
        album_feed = requests.get(url_albums, headers=self.headers).text

        albums = {}
        root = ElementTree.fromstring(album_feed)
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            if title not in albums:
                albums[title] = {}
            albums[title]["id"] = entry.find("{http://schemas.google.com/photos/2007}id").text

        return albums

    def get_photos(self, albumID):
        photos_feed = requests.get(url_albums + "/albumid/" + albumID, headers=self.headers).text

        photos = {}
        root = ElementTree.fromstring(photos_feed)
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            if title not in photos:
                photos[title] = {}
            photos[title]["id"] = entry.find("{http://schemas.google.com/photos/2007}id").text

        return photos

    def create_album(self, title):
        pass

    def upload(self, photofile, filename, albumID):
        pass
