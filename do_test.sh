#!/bin/sh

rm -rf env

virtualenv env -p /usr/bin/python2
env/bin/pip install -r requirements.txt
env/bin/nosetests

rm -rf env

virtualenv env -p /usr/bin/python3
env/bin/pip install -r requirements.txt
env/bin/nosetests

