#!python

import httpretty
import os.path
import flickrapi

from os import mkdir, rename
from shutil import rmtree
from unittest import TestCase
from mock import Mock
from io import StringIO
from datetime import datetime
from xml.etree import ElementTree

from photoriver.receivers import FolderReceiver, FlashAirReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FolderUploader, FlickrUploader

class BasicTest(TestCase):
    def test_reality(self):
        self.assertTrue(2+2==4)


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
            f.write("DUMMY JPEG FILE HEADER")
        
        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])
        cached_file = self.receiver.download_file('IMG_123.JPG')
        self.assertEqual(repr(cached_file), "Photo(./IMG_123.JPG)")
        with cached_file.open_file() as f:
            data = f.read()
        
        self.assertEqual(data, "DUMMY JPEG FILE HEADER")
        cached_file = self.receiver.download_file('IMG_123.JPG')
        with cached_file.open_file() as f:
            data = f.read()
        
        self.assertEqual(data, "DUMMY JPEG FILE HEADER")
    
    def test_add_file_offline(self):
        with open("test_folder/IMG_123.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER")
        
        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])
        rename("test_folder", "other_folder")
        self.assertEqual(list(self.receiver.get_list().keys()), ['IMG_123.JPG'])

        with open("other_folder/IMG_124.JPG", "w") as f:
            f.write("DUMMY JPEG FILE HEADER 2")

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
        httpretty.disable()
        self.assertFalse(self.receiver.is_available())
        httpretty.enable()
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
        
        httpretty.disable()
        file_list = self.receiver.get_list()
        self.assertEqual(sorted(list(file_list.keys())), ["IMG_123.JPG", "IMG_124.JPG"])
        self.assertEqual(file_list["IMG_123.JPG"].timestamp, datetime(2013, 5, 15, 13, 44, 16))
        self.assertEqual(file_list["IMG_124.JPG"].timestamp, datetime(2013, 5, 15, 13, 44, 18))
        httpretty.enable()
    
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
        
        self.assertEqual(data, "JPEG DUMMY TEST DATA 1")
        cached_file = self.receiver.download_file('IMG_123.JPG')
        with cached_file.open_file() as f:
            data = f.read()
        
        self.assertEqual(data, "JPEG DUMMY TEST DATA 1")
        
    
        

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
        
        self.uploader.upload(photo_obj)
        
        self.assertTrue(os.path.exists("upload_folder/IMG_123.JPG"))
        with open("upload_folder/IMG_123.JPG") as f:
            data = f.read()
        self.assertEqual(data, "JPEG DUMMY TEST DATA")

class MockFlickrAPI(Mock):
    _called={}

    def get_token_part_one(self, perms):
        return ("token", "frob")

    def get_token_part_two(self, tokens):
        return
    
    def upload(self, filename, title="123"):
        self._called['upload'] = filename
        return ElementTree.fromstring('<rsp stat="ok">\n<photoid>13827599313</photoid>\n</rsp>')
    
    def photosets_create(self, name, primary_photo_id):
        self._called['created.name'] = name
        self._called['created.primary_photo_id'] = primary_photo_id
        return ElementTree.fromstring('<rsp stat="ok">\n<photoset id="72157643905570745" url="http://www.flickr.com/photos/aigarius/sets/72157643905570745/" />\n</rsp>')
     
    def photosets_getList(self):
        string = """<rsp stat="ok">
<photosets cancreate="1" page="1" pages="1" perpage="42" total="42">
	<photoset can_comment="1" count_comments="0" count_views="0" date_create="1397413231" date_update="0" farm="6" id="72157643905570745" needs_interstitial="0" photos="1" primary="13827599313" secret="aa00f81f9d" server="5164" videos="0" visibility_can_see_set="1">
		<title>Test 123</title>
		<description />
	</photoset>
	<photoset can_comment="1" count_comments="0" count_views="1" date_create="1395533894" date_update="1395533914" farm="4" id="72157642764389724" needs_interstitial="0" photos="308" primary="11910296655" secret="a3456ac147" server="3749" videos="1" visibility_can_see_set="1">
		<title>nonset</title>
		<description />
	</photoset>
	<photoset can_comment="1" count_comments="0" count_views="87" date_create="1392560704" date_update="1392560766" farm="8" id="72157641062521883" needs_interstitial="0" photos="1310" primary="12559920665" secret="e2b3b7879a" server="7289" videos="0" visibility_can_see_set="1">
		<title>Hong Kong trip</title>
		<description>with side trips to Tokyo and Macao</description>
	</photoset>
</photosets>
</rsp>
        """
        return ElementTree.fromstring(string)

class FlickrUploaderTest(TestCase):
    def setUp(self):
        flickrapi.FlickrAPI = MockFlickrAPI
        self.uploader = FlickrUploader(set_name="Photoriver Test 123")
    
    def tearDown(self):
        rmtree(".cache", ignore_errors=True)
    
    def test_upload(self):
        photo_obj = Mock(file_name="IMG_123.JPG", _cached_file=".cache/IMG_123.JPG")
        photo_file = StringIO(u"JPEG DUMMY TEST DATA")
        photo_obj.open_file.return_value = photo_file
        
        self.uploader.upload(photo_obj)
        
        self.assertEqual(self.uploader.api._called['upload'], ".cache/IMG_123.JPG")
        self.assertEqual(self.uploader.api._called['created.name'], "Photoriver Test 123")
        self.assertEqual(self.uploader.api._called['created.primary_photo_id'], 13827599313)
    

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
            f.write("DUMMY JPEG FILE HEADER")
                
        controller = BasicController(receiver=receiver, uploaders=[uploader])
        controller.process_all()

        self.assertTrue(os.path.exists("upload_folder/IMG_123.JPG"))
        with open("upload_folder/IMG_123.JPG") as f:
            data = f.read()
        self.assertEqual(data, "DUMMY JPEG FILE HEADER")
        
        
        
        
        
        
        
        
        
