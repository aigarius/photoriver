photoriver
==========

[![Build Status](https://travis-ci.org/aigarius/photoriver.svg?branch=master)](https://travis-ci.org/aigarius/photoriver)
[![Coverage Status](https://coveralls.io/repos/aigarius/photoriver/badge.png?branch=master)](https://coveralls.io/r/aigarius/photoriver?branch=master)

System for streamlinging photographic process with networked cameras. Deep ToDo country so far :)


The basic system consists of:
* one of the possible receiver modules, like the basic FolderReceiver or remote FlashAir receiver
* zero or more filters runnign trought each message adding or changing data, such as GpsTagger, DateCorrection
* one or more uploader modules, like the basic FolderUploader or remote Flickr and GooglePlus uploaders

There two distinct workflows: live event and travel pictures.

In both cases I want the images to retain the file names, Exif information and timing of the original photos and also have embedded GPS information from the phone synced to the time the photo was taken. And if I take a burst of very similar photos, I want the uploading process to only select and upload the "best" one (trivial heiristic being the file size) with an ability for me to later choose another one to replace it. There would need to be some way of syncing phone and camera time, especially considering that phones usually switch to local time zone when traveling and cameras do not, maybe the original time the photo was taken would need to be changed to local time zone, so that there are no photos that are taken during the day, but have a timestamp of 23:45 GMT.

When I am in Live Event mode I would like the photos that I take to immediately start uploading to an event album that I create (or choose) at the start of the shoot with a preset privacy mode. This assumes that either I am willing to upload via 3G of my phone or that I have access to a stable WiFi network on-site. It might be good if I could upload a scaled down version of the pictures during the event and then later replace the image files with full-size images when the even is over and I am at home in my high-speed network. I probably don't need the full size files on my phone.

When I am in Travel mode, I want to delay photo uploading until I am back at the hotel with its high speed Wifi, but also have an option to share some snapshots immediately over 3G or random cafe Wifi. I am likely to take more photos that there is memory in my phone, so I would like to clear original files from the phone while keeping them in the SD card and in the cloud, but still keeping enough metadata to allow re-uploading an image or choosing another image in a burst.

Implementation tagets (in priority order):
 * Python based, Live Event mode moving the images between two folders;
 * FlashAir receiver;
 * Google+ album uploader;
 * Best-in-burst selection filter;
 * GPS Tagging filter with a hard-coded location;
 * Date fixing filter with a hard-coded offset;
 * Flick uploader;
 * Chooser command to change choise of best-in-burst;
 * ...
 * Android port

Non-functional requirements:
 * 100% test coverage;
 * test-driven development;
 * parallel processing;
 * fault tolerance;
 * detailed logging;
 * restartability;
