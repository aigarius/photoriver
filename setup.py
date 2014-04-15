import os.path as path
from setuptools import setup


def get_readme(filename):
    if not path.exists(filename):
        return ""

    with open(path.join(path.dirname(__file__), filename)) as readme:
        content = readme.read()
    return content

setup(name="photoriver",
      version="0.1",
      author="Aigars Mahinovs",
      author_email="aigarius@gmail.com",
      description="System for streamlinging photographic process with networked cameras",
      license="GPLv3",
      keywords="phot wifi",
      url="https://github.com/aigarius/photoriver",
      packages=["photoriver"],
      long_description=get_readme("README.md"),
      classifiers=[
          "Topic :: Multimedia :: Graphics :: Capture :: Digital Camera",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: Implementation :: PyPy",
          "Development Status :: 4 - Beta",
          "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
      ],
      install_requires=["mock", "nose", "requests", "HTTPretty"],
      dependency_links=[
          "http://bitbucket.org/sybren/flickrapi/get/tip.zip#egg=flickrapi",
          "https://aigarius-gdata.googlecode.com/archive/tip.zip#egg=gdata",
      ],
      test_suite="photoriver.tests",
      )
