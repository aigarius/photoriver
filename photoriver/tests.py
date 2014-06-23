#!python

import httpretty
import os.path
import flickrapi
import json
import requests
import logging
import six

from os import mkdir, rename, remove
from shutil import rmtree
from unittest import TestCase
from mock import Mock, patch
from io import StringIO, open
from datetime import datetime
from xml.etree import ElementTree

from photoriver.receivers import FolderReceiver, FlashAirReceiver
from photoriver.filters import GPSTagFilter
from photoriver.controllers import BasicController
from photoriver.uploaders import FolderUploader, FlickrUploader, GPlusUploader
from photoriver.gplusapi import GPhoto

logging.basicConfig(level=logging.CRITICAL)


class BasicTest(TestCase):
    def test_reality(self):
        self.assertTrue(2 + 2 == 4)


class ReceiverTest(TestCase):
    def setUp(self):
        mkdir("test_folder")
        self.receiver = FolderReceiver("test_folder/")

    def tearDown(self):
        rmtree("test_folder", ignore_errors=True)
        rmtree(".cache", ignore_errors=True)

    def test_nodata(self):
        rmtree("test_folder")
        self.assertEqual(self.receiver.get_list(), {})
        self.assertFalse(self.receiver.is_available())
        mkdir("test_folder")
        self.assertEqual(self.receiver.get_list(), {})
        self.assertTrue(self.receiver.is_available())

    def test_add_file(self):
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write(u"DUMMY JPEG FILE HEADER")

        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])
        cached_file = self.receiver.download_file('IMG_123.JPG')
        self.assertEqual(repr(cached_file), "Photo(./IMG_123.JPG)")
        with cached_file.open_file() as f:
            data = f.read()

        self.assertEqual(data, u"DUMMY JPEG FILE HEADER")
        cached_file = self.receiver.download_file('IMG_123.JPG')
        with cached_file.open_file() as f:
            data = f.read()

        self.assertEqual(data, u"DUMMY JPEG FILE HEADER")

    def test_add_file_offline(self):
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write(u"DUMMY JPEG FILE HEADER")

        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])
        rename("test_folder", "other_folder")
        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])

        with open("other_folder/IMG_124.JPG", "w") as f:
            f.write(u"DUMMY JPEG FILE HEADER 2")

        rename("other_folder", "test_folder")
        self.assertEqual(sorted(self.receiver.get_list().keys()), ['IMG_123.JPG', 'IMG_124.JPG'])


class FlashAirReceiverTest(TestCase):
    def setUp(self):
        httpretty.enable()
        self.files = {}
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/command.cgi",
                               body=self.callback)

        self.receiver = FlashAirReceiver(url="http://192.168.34.72/", timeout=0.01)

    def callback(self, method, uri, headers):
        if uri == "http://192.168.34.72/command.cgi?op=120":
            return (200, headers, "02544d535730384708c00b78700d201")

        if uri == "http://192.168.34.72/command.cgi?op=102":
            return (200, headers, "1")

        if uri == "http://192.168.34.72/command.cgi?op=100&DIR=/DCIM/102CANON":
            lines = ["WLANSD_FILELIST"]
            lines += [",".join(("/DCIM", x, str(y['size']), str(32), str(y['adate']), str(y['atime']))) for x, y in self.files.items()]
            lines += ['']
            text = "\n".join(lines)
            return (200, headers, text)

    def tearDown(self):
        rmtree(".cache", ignore_errors=True)
        httpretty.disable()  # disable afterwards, so that you will have no problems in code that uses that socket module
        httpretty.reset()    # reset HTTPretty state (clean up registered urls and request history)

    def test_availability(self):
        self.assertTrue(self.receiver.is_available())
        self.assertTrue(self.receiver.is_available())
        httpretty.reset()
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/command.cgi",
                               body="ERROR", status=404)
        self.assertFalse(self.receiver.is_available())
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/command.cgi",
                               body=self.callback)
        self.assertTrue(self.receiver.is_available())

    def test_file_lists(self):
        self.assertEqual(self.receiver.get_list(), {})

        self.files = {
            "IMG_123.JPG": {"size": 123, "adate": 17071, "atime": 28040},
            "IMG_124.JPG": {"size": 125, "adate": 17071, "atime": 28041},
        }

        file_list = self.receiver.get_list()
        self.assertEqual(sorted(list(file_list.keys())), ["IMG_123.JPG", "IMG_124.JPG"])
        self.assertEqual(file_list["IMG_123.JPG"].timestamp, datetime(2013, 5, 15, 13, 44, 16))
        self.assertEqual(file_list["IMG_124.JPG"].timestamp, datetime(2013, 5, 15, 13, 44, 18))

        httpretty.reset()
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/command.cgi",
                               body="ERROR", status=404)
        file_list = self.receiver.get_list()
        self.assertEqual(sorted(list(file_list.keys())), ["IMG_123.JPG", "IMG_124.JPG"])
        self.assertEqual(file_list["IMG_123.JPG"].timestamp, datetime(2013, 5, 15, 13, 44, 16))
        self.assertEqual(file_list["IMG_124.JPG"].timestamp, datetime(2013, 5, 15, 13, 44, 18))
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/command.cgi",
                               body=self.callback)

    def test_file_list_errors(self):
        self.files = {
            "IMG_123.JPG": {"size": 123, "adate": 17071, "atime": 28040},
            "IMG_124.JPG": {"size": 125, "adate": 17071, "atime": 28041},
        }
        file_list = self.receiver.get_list()
        self.assertEqual(sorted(list(file_list.keys())), ["IMG_123.JPG", "IMG_124.JPG"])
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/command.cgi",
                               body="Bad data")
        self.assertEqual(self.receiver.get_list(), file_list)
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/command.cgi",
                               body="WLANSD_FILELIST", status=404)
        self.assertEqual(self.receiver.get_list(), file_list)

    def test_download(self):
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/DCIM/IMG_123.JPG",
                               body="JPEG DUMMY TEST DATA 1")
        httpretty.register_uri(httpretty.GET, "http://192.168.34.72/DCIM/IMG_124.JPG",
                               body="JPEG DUMMY TEST DATA 2")
        self.files = {
            "IMG_123.JPG": {"size": 123, "adate": 17071, "atime": 28040},
            "IMG_124.JPG": {"size": 125, "adate": 17071, "atime": 28041},
        }

        file_list = self.receiver.get_list()

        self.assertEqual(self.receiver._files['IMG_123.JPG'].open_file(), None)

        cached_file = self.receiver.download_file('IMG_123.JPG')
        with cached_file.open_file() as f:
            data = f.read()

        self.assertEqual(data, u"JPEG DUMMY TEST DATA 1")
        cached_file = self.receiver.download_file('IMG_123.JPG')
        with cached_file.open_file() as f:
            data = f.read()

        self.assertEqual(data, u"JPEG DUMMY TEST DATA 1")


class ControllerTest(TestCase):
    def setUp(self):
        self.receiver = Mock()
        self.filter1 = Mock()
        self.filter2 = Mock()
        self.uploader = Mock()
        self.controller = BasicController(receiver=self.receiver, filters=[self.filter1, self.filter2], uploaders=[self.uploader])

    def tearDown(self):
        rmtree(".cache", ignore_errors=True)

    def test_nodata(self):
        self.receiver.get_list.return_value = {}

        self.controller.process_all()

        self.receiver.get_list.assert_called_once_with()

    def test_basic_filtration(self):
        mock1 = Mock(file_name="IMG_123.JPG")
        mock2 = Mock(file_name="IMG_123.JPG", _cached=True)
        mock3 = Mock(file_name="IMG_123.JPG", _cached=True, gps_data="something")
        mock4 = Mock(file_name="IMG_123.JPG", _cached=True, gps_data="something", title="Dude!")
        self.receiver.get_list.return_value = {'IMG_123.JPG': mock1}
        self.receiver.is_available.return_value = True
        self.receiver.download_file.return_value = mock2
        self.filter1.filter.return_value = mock3
        self.filter2.filter.return_value = mock4

        self.controller.process_all()

        self.receiver.download_file.assert_called_once_with("IMG_123.JPG")
        self.filter1.filter.assert_called_once_with(mock2)
        self.filter2.filter.assert_called_once_with(mock3)
        self.uploader.upload.assert_called_once_with(mock4)


class GPSTagFilterTest(TestCase):
    def setUp(self):
        self.filter = GPSTagFilter()
        self.filter.gpshistory = {
            datetime(2014, 05, 01, 14, 00, 00): {'lat': 50.0, 'lon': 24.0, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 01, 14, 01, 00): {'lat': 50.1, 'lon': 24.1, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 01, 14, 02, 00): {'lat': 50.2, 'lon': 24.1, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 01, 14, 02, 01): {'lat': 50.3, 'lon': 23.0, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 01, 14, 03, 00): {'lat': 50.4, 'lon': 23.1, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 01, 14, 04, 00): {'lat': 50.0, 'lon': -22.0, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 01, 14, 04, 00): {'lat': 50.0, 'lon': -22.0, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 01, 14, 04, 02): {'lat': 50.5, 'lon': -22.9, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 02, 14, 00, 00): {'lat': 50.1, 'lon': -22.1, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 02, 14, 01, 00): {'lat': 50.2, 'lon': -22.2, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
            datetime(2014, 05, 02, 14, 02, 00): {'lat': 50.3, 'lon': -22.3, 'altitude': 30.0, 'bearing': 15.0, 'speed': 5.0},
        }

    def test_location_selection_no_history(self):
        self.filter.gpshistory = {}
        self.assertIsNone(self.filter.select_location(datetime(2014, 05, 01, 14, 04, 00)))

    def test_location_selection_no_data(self):
        self.assertIsNone(self.filter.select_location(datetime(2013, 01, 01, 01, 01, 01)))

    def test_location_selection_exact_match(self):
        self.assertDictContainsSubset({'lat': 50.2, 'lon': 24.1}, self.filter.select_location(datetime(2014, 05, 01, 14, 02, 00)))
        self.assertDictContainsSubset({'lat': 50.3, 'lon': 23.0}, self.filter.select_location(datetime(2014, 05, 01, 14, 02, 01)))

    def test_location_selection_early_data(self):
        self.assertDictContainsSubset({'lat': 50.3, 'lon': -22.3}, self.filter.select_location(datetime(2014, 05, 03, 14, 02, 00)))
        self.assertDictContainsSubset({'lat': 50.0, 'lon': -22.0}, self.filter.select_location(datetime(2014, 05, 01, 14, 04, 01)))
        self.assertDictContainsSubset({'lat': 50.4, 'lon': 23.1}, self.filter.select_location(datetime(2014, 05, 01, 14, 03, 01)))
        self.assertDictContainsSubset({'lat': 50.4, 'lon': 23.1}, self.filter.select_location(datetime(2014, 05, 01, 14, 03, 31)))
        self.assertDictContainsSubset({'lat': 50.4, 'lon': 23.1}, self.filter.select_location(datetime(2014, 05, 01, 14, 03, 50)))

    def test_location_selection_late_data(self):
        self.assertDictContainsSubset({'lat': 50.0, 'lon': -22.0}, self.filter.select_location(datetime(2014, 05, 01, 14, 03, 56)))
        self.assertDictContainsSubset({'lat': 50.1, 'lon': -22.1}, self.filter.select_location(datetime(2014, 05, 02, 13, 03, 56)))


class UploaderTest(TestCase):
    def setUp(self):
        self.uploader = FolderUploader("upload_folder/")

    def tearDown(self):
        rmtree(".cache", ignore_errors=True)
        rmtree("upload_folder", ignore_errors=True)

    def test_upload(self):
        photo_obj = Mock(file_name="IMG_123.JPG")
        photo_file = StringIO(u"JPEG DUMMY TEST DATA")
        photo_obj.open_file.return_value = photo_file

        f = self.uploader.upload(photo_obj)
        f.result()

        self.assertTrue(os.path.exists("upload_folder/IMG_123.JPG"))
        with open("upload_folder/IMG_123.JPG") as f:
            data = f.read()
        self.assertEqual(data, u"JPEG DUMMY TEST DATA")


class MockFlickrAPI(Mock):
    _called = {}
    token_cache = Mock(token=Mock(
        token=u"cached_token_123",
        token_secret=u"secret",
        access_level=u"write",
        fullname=u"Full Name",
        username=u"username",
        user_nsid=u"N934Ussefjs",
    ))

    def token_valid(self, perms):
        return self.token_cache.token.token == u"cached_token_234"

    def get_request_token(self, oauth_callback):
        return u"request_token"

    def auth_url(self, perms):
        return u"http://example.com/auth_url"

    def get_access_token(self, verifier):
        self.token_cache.token.token = u"cached_token_234"

    def upload(self, filename, title="123"):
        self._called['upload'] = filename
        return ElementTree.fromstring('<rsp stat="ok">\n<photoid>13827599313</photoid>\n</rsp>')

    def photosets_create(self, title, primary_photo_id):
        self._called['created.title'] = title
        self._called['created.primary_photo_id'] = primary_photo_id
        return ElementTree.fromstring('''
<rsp stat="ok">
    <photoset id="72157643905570745" url="http://www.flickr.com/photos/aigarius/sets/72157643905570745/" />
</rsp>
        ''')

    def photosets_getList(self):
        string = """<rsp stat="ok">
<photosets cancreate="1" page="1" pages="1" perpage="42" total="42">
        """
        if "created.title" in self._called:
            string += """
    <photoset can_comment="1" count_comments="0" count_views="0" date_create="1397413231" date_update="0" farm="6" id="72157643905570745" \
    needs_interstitial="0" photos="1" primary="13827599313" server="5164" videos="0" visibility_can_see_set="1">
        <title>Photoriver Test 123</title>
        <description />
    </photoset>
            """
        string += """
    <photoset can_comment="1" count_comments="0" count_views="1" date_create="1395533894" date_update="1395533914" farm="4" id="72157642764389724" \
    needs_interstitial="0" photos="308" primary="11910296655" server="3749" videos="1" visibility_can_see_set="1">
        <title>nonset</title>
        <description />
    </photoset>
    <photoset can_comment="1" count_comments="0" count_views="87" date_create="1392560704" date_update="1392560766" farm="8" id="72157641062521883" \
    needs_interstitial="0" photos="1310" primary="12559920665" server="7289" videos="0" visibility_can_see_set="1">
        <title>Hong Kong trip</title>
        <description>with side trips to Tokyo and Macao</description>
    </photoset>
</photosets>
</rsp>
        """
        return ElementTree.fromstring(string)

    def photosets_addPhoto(self, photoset_id, photo_id):
        self._called['addPhoto.photoset_id'] = photoset_id
        self._called['addPhoto.photo_id'] = photo_id
        return ElementTree.fromstring('<rsp stat="ok">\n</rsp>')


class FlickrUploaderTest(TestCase):
    def setUp(self):
        flickrapi.FlickrAPI = MockFlickrAPI
        with patch("six.moves.input") as input_mock:
            input_mock.return_value = b"1234-5678"

            self.uploader = FlickrUploader(set_name="Photoriver Test 123")

    def tearDown(self):
        rmtree(".cache", ignore_errors=True)
        remove("token.cache")

    def test_upload(self):
        photo_obj = Mock(file_name="IMG_123.JPG", _cached_file=".cache/IMG_123.JPG")
        photo_file = StringIO(u"JPEG DUMMY TEST DATA")
        photo_obj.open_file.return_value = photo_file

        f = self.uploader.upload(photo_obj)
        f.result()

        self.assertEqual(self.uploader.api._called['upload'], ".cache/IMG_123.JPG")
        self.assertEqual(self.uploader.api._called['created.title'], "Photoriver Test 123")
        self.assertEqual(self.uploader.api._called['created.primary_photo_id'], 13827599313)

        photo_obj = Mock(file_name="IMG_124.JPG", _cached_file=".cache/IMG_124.JPG")

        f = self.uploader.upload(photo_obj)
        f.result()

        self.assertEqual(self.uploader.api._called['upload'], ".cache/IMG_124.JPG")
        self.assertEqual(self.uploader.api._called['addPhoto.photoset_id'], 72157643905570745)
        self.assertEqual(self.uploader.api._called['addPhoto.photo_id'], 13827599313)

    def test_caching(self):
        self.uploader = FlickrUploader(set_name="Photoriver Test 123")
        self.uploader.api.token_cache.token.token = "bad_token"

        with patch("six.moves.input") as input_mock:
            input_mock.return_value = b"1234-5678"
            self.uploader = FlickrUploader(set_name="Photoriver Test 123")


gphoto_albums_xml = open("photoriver/testdata/galbums.xml", encoding="utf8").read()
gphoto_photos_xml = open("photoriver/testdata/gphotos.xml", encoding="utf8").read()


class GPhotoApiTest(TestCase):
    def setUp(self):
        httpretty.enable()
        self.token_data = {
            "access_token": "1/fFAGRNJru1FTz70BzhT3Zg",
            "expires_in": 3920,
            "token_type": "Bearer",
            "refresh_token": "1/xEoDL4iW3cxlI7yDbSRFYNG01kVKM2C-259HOF2aQbI"
        }
        httpretty.register_uri(httpretty.POST, "https://accounts.google.com/o/oauth2/token", body=json.dumps(self.token_data))
        with patch("six.moves.input") as input_mock:
            input_mock.return_value = b"1234-5678"
            self.api = GPhoto()

    def tearDown(self):
        rmtree(".cache", ignore_errors=True)
        remove("token.cache")
        httpretty.disable()  # disable afterwards, so that you will have no problems in code that uses that socket module
        httpretty.reset()    # reset HTTPretty state (clean up registered urls and request history)

    def test_gphoto_api(self):

        self.assertEqual(httpretty.last_request().parsed_body["code"][0], "1234-5678")
        with open("token.cache", "r") as f:
            self.assertIn(self.token_data["refresh_token"], f.read())

        self.api = GPhoto()
        self.assertEqual(httpretty.last_request().parsed_body["refresh_token"][0], self.token_data["refresh_token"])

        httpretty.register_uri(httpretty.GET, "https://picasaweb.google.com/data/feed/api/user/default", body=gphoto_albums_xml)
        httpretty.register_uri(httpretty.GET,
                               "https://picasaweb.google.com/data/feed/api/user/default/albumid/5992553397538619153",
                               body=gphoto_photos_xml
                               )

        albums = self.api.get_albums()
        self.assertIn("Tampere high and dry", albums.keys())

        photos = self.api.get_photos(albums["Tampere high and dry"]["id"])
        self.assertEqual(len(photos), 18)
        self.assertIn("20110815_174429_100-6804.jpg", photos.keys())

        httpretty.register_uri(httpretty.POST, "https://picasaweb.google.com/data/feed/api/user/default", status=201)
        httpretty.register_uri(httpretty.POST,
                               "https://picasaweb.google.com/data/feed/api/user/default/albumid/5992553397538619153",
                               status=201)

        self.assertTrue(self.api.create_album("Test 123"))

        with open("IMG_123.JPG", "w") as f:
            f.write(u"DUMMY JPEG FILE HEADER")
        self.assertTrue(self.api.upload("IMG_123.JPG", "IMG_321", albums["Tampere high and dry"]["id"]))
        remove("IMG_123.JPG")

    def test_gphoto_exceptions(self):

        with open("token.cache", "wb") as f:
            f.write(b"BAD JSON")

        with patch("six.moves.input") as input_mock:
            input_mock.return_value = b"1234-5678"

            self.api = GPhoto()
        self.assertEqual(httpretty.last_request().parsed_body["code"][0], "1234-5678")


class GPhotoTest(TestCase):
    def test_gphoto(self):
        api_obj = Mock()
        api_obj.get_albums.side_effect = [{}, {"Test 123": {"id": "23456"}}, {"Test 123": {"id": "23456"}}, {"Test 123": {"id": "23456"}}]
        api_obj.get_photos.return_value = {}
        api_obj.create_album.return_value = True
        with patch("photoriver.uploaders.GPhoto") as api_mock:
            api_mock.return_value = api_obj
            with patch("six.moves.input") as input_mock:
                input_mock.return_value = b"1234-5678"

                # With album creation
                uploader = GPlusUploader("Test 123")
                api_obj.create_album.assert_called_once_with("Test 123")
                self.assertEqual(api_obj.get_albums.call_count, 2)

                # With existing album
                uploader = GPlusUploader("Test 123")
                api_obj.create_album.assert_called_once_with("Test 123")
                self.assertEqual(api_obj.get_albums.call_count, 3)

                # With existing photos
                api_obj.get_photos.return_value = {"IMG_122.JPG": {"id": 122}}
                uploader = GPlusUploader("Test 123")
                api_obj.create_album.assert_called_once_with("Test 123")
                self.assertEqual(api_obj.get_albums.call_count, 4)

        photo_obj = Mock(file_name="IMG_122.JPG", _cached_file=".cache/IMG_122.JPG")
        photo_file = StringIO(u"JPEG DUMMY TEST DATA")
        photo_obj.open_file.return_value = photo_file

        f = uploader.upload(photo_obj)
        f.result()

        self.assertFalse(api_obj.upload.called)

        photo_obj = Mock(file_name="IMG_123.JPG", _cached_file=".cache/IMG_123.JPG")
        photo_file = StringIO(u"JPEG DUMMY TEST DATA")
        photo_obj.open_file.return_value = photo_file

        f = uploader.upload(photo_obj)
        f.result()

        api_obj.upload.assert_called_once_with(".cache/IMG_123.JPG", "IMG_123.JPG", "23456")


class IntegrationTest(TestCase):
    def tearDown(self):
        rmtree(".cache", ignore_errors=True)
        rmtree("test_folder", ignore_errors=True)
        rmtree("upload_folder", ignore_errors=True)

    def test_basic_pipeline(self):
        mkdir("test_folder")
        receiver = FolderReceiver("test_folder/")
        uploader = FolderUploader("upload_folder/")
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write(u"DUMMY JPEG FILE HEADER")

        controller = BasicController(receiver=receiver, uploaders=[uploader])
        controller.process_all()
        for future in controller.futures:
            future.result()

        self.assertTrue(os.path.exists("upload_folder/IMG_123.JPG"))
        with open("upload_folder/IMG_123.JPG") as f:
            data = f.read()
        self.assertEqual(data, u"DUMMY JPEG FILE HEADER")
