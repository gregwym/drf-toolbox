from __future__ import absolute_import, unicode_literals
from os.path import dirname, realpath


with open(realpath(dirname(__file__)) + '/.VERSION', 'r') as version_file:
    __version__ = version_file.read().strip()
