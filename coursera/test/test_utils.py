# -*- coding: utf-8 -*-

"""
Test the utility functions.
"""

import os.path
import unittest

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
