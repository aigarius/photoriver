#!python

import httpretty
import os.path

from os import mkdir, rename
from shutil import rmtree
from unittest import TestCase
from mock import Mock
from io import StringIO
from datetime import datetime

from photoriver.receivers import FolderReceiver, FlashAirReceiver
from photoriver.controllers import BasicController
from photoriver.uploaders import FolderUploader

class BasicTest(TestCase):
    def basic_test(self):
        self.assertTrue(2+2==4)


class ReceiverTest(TestCase):
    def setUp(self):
        mkdir("test_folder")
        self.receiver = FolderReceiver("test_folder/")
    
    def tearDown(self):
        rmtree("test_folder", ignore_errors=True)
    
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
        
        self.receiver = FlashAirReceiver(url="http://192.168.34.72/")
       
    def callback(self, method, uri, headers):
        if uri == "http://192.168.34.72/command.cgi?op=120":
            return (200, headers, "02544d535730384708c00b78700d201")
        if uri == "http://192.168.34.72/command.cgi?op=100&dir=/DCIM":
            lines = ["WLANSD_FILELIST"]
            lines += [",".join(("/DCIM", x, str(y['size']), str(32), str(y['adate']), str(y['atime']))) for x, y in self.files.items()]
            text = "\n".join(lines)
            return (200, headers, text)

    def tearDown(self):
        httpretty.disable()  # disable afterwards, so that you will have no problems in code that uses that socket module
        httpretty.reset()    # reset HTTPretty state (clean up registered urls and request history)

    def test_availability(self):
        self.assertTrue(self.receiver.is_available())
        self.assertTrue(self.receiver.is_available())
        self.receiver = FlashAirReceiver(url="http://192.168.34.72/", timeout=0.01)
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
        self.assertEqual(file_list.keys(), ["IMG_123.JPG", "IMG_124.JPG"])
        self.assertEqual(file_list["IMG_123.JPG"].timestamp, datetime(2013, 5, 15, 13, 44, 16))
        self.assertEqual(file_list["IMG_124.JPG"].timestamp, datetime(2013, 5, 15, 13, 44, 18))
    
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
        
class IntegrationTest(TestCase):
    def tearDown(self):
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
        
        
        
        
        
        
        
        
        
