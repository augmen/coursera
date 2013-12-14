#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test syllabus parsing.
"""

from __future__ import unicode_literals

import os.path
import unittest

from coursera import cookies

FIREFOX_COOKIES = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "cookies", "firefox_cookies.txt")

CHROME_COOKIES = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "cookies", "chrome_cookies.txt")

FIREFOX_COOKIES_WITHOUT_COURSERA = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "cookies", "firefox_cookies_without_coursera.txt")

FIREFOX_COOKIES_EXPIRED = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "cookies", "firefox_cookies_expired.txt")


class MockResponse:
    def raise_for_status(self):
        pass


class MockSession:
    def __init__(self):
        self.called = False

    def get(self, url):
        self.called = True
        return MockResponse()


class CookiesFileTestCase(unittest.TestCase):

    def test_load_firefox_cookies(self):
        from six.moves import http_cookiejar as cookielib
        cj = cookies.load(FIREFOX_COOKIES)
        self.assertTrue(isinstance(cj, cookielib.MozillaCookieJar))

    def test_load_chrome_cookies(self):
        from six.moves import http_cookiejar as cookielib
        cj = cookies.load(CHROME_COOKIES)
        self.assertTrue(isinstance(cj, cookielib.MozillaCookieJar))

    def test_find_cookies_for_course(self):
        import requests
        cj = cookies.read_for_course(FIREFOX_COOKIES, 'course-001')
        self.assertTrue(isinstance(cj, requests.cookies.RequestsCookieJar))

        self.assertEquals(len(cj), 6)

        domains = cj.list_domains()
        self.assertEquals(len(domains), 2)
        self.assertTrue('.coursera.org' in domains)
        self.assertTrue('class.coursera.org' in domains)

        paths = cj.list_paths()
        self.assertEquals(len(paths), 2)
        self.assertTrue('/' in paths)
        self.assertTrue('/course-001' in paths)

    def test_read_for_course(self):
        import requests
        cj = cookies.read_for_course(
            FIREFOX_COOKIES_WITHOUT_COURSERA, 'course-001')
        self.assertTrue(isinstance(cj, requests.cookies.RequestsCookieJar))

        self.assertEquals(len(cj), 0)

    def test_read_cookies_for_course_with_expired_cookies(self):
        import requests
        cj = cookies.read_for_course(
            FIREFOX_COOKIES_EXPIRED, 'course-001')
        self.assertTrue(isinstance(cj, requests.cookies.RequestsCookieJar))

        self.assertEquals(len(cj), 2)

    def test_has_course_cookies(self):
        cj = cookies.read_for_course(FIREFOX_COOKIES, 'course-001')

        enough = cookies.has_course_cookies(cj, 'course-001')
        self.assertTrue(enough)

    def test_has_course_cookies_failed(self):
        cj = cookies.read_for_course(
            FIREFOX_COOKIES_WITHOUT_COURSERA, 'course-001')

        enough = cookies.has_course_cookies(cj, 'course-001')
        self.assertFalse(enough)
