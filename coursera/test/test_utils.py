# -*- coding: utf-8 -*-

"""
Test the utility functions.
"""

from __future__ import unicode_literals

import os.path
import unittest

from six import iteritems

from coursera import utils

NETRC = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "auth", "netrc")

NOT_NETRC = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "auth", "not_netrc")


class UtilsTestCase(unittest.TestCase):

    def test_netrc_credentials_with_valid_file(self):
        username, password = utils.netrc_credentials(NETRC)
        self.assertEquals(username, 'user@mail.com')
        self.assertEquals(password, 'secret')

    def test_netrc_credentials_with_invalid_file(self):
        credentials = utils.netrc_credentials(NOT_NETRC)
        self.assertEquals(credentials, None)

    def test_resource_filename_from_url(self):
        strings = {
            'https://c.c/l/subtitles?q=19_en&format=txt': 'subtitles.txt',
            'https://c.c/l/subtitles?q=19_en&format=srt': 'subtitles.srt',
            'https://d.c/slides%2F14test.pdf': 'slides-14test.pdf',
            'https://c.c.org/download.mp4?lecture_id=123': 'video.mp4'
        }
        for k, v in iteritems(strings):
            self.assertEquals(utils.resource_filename_from_url(k), v)

    def test_clean_url_ads_scheme(self):
        url = "www.coursera.org"
        self.assertEquals(utils.clean_url(url), 'http://www.coursera.org')

        url = " www.coursera.org"
        self.assertEquals(utils.clean_url(url), 'http://www.coursera.org')

    def test_clean_url_does_not_removes_scheme(self):
        url = "ftp://www.coursera.org "
        self.assertEquals(utils.clean_url(url), 'ftp://www.coursera.org')

    def test_clean_url_empty_url(self):
        url = None
        self.assertEquals(utils.clean_url(url), None)

        url = " "
        self.assertEquals(utils.clean_url(url), "")

        url = ""
        self.assertEquals(utils.clean_url(url), "")
