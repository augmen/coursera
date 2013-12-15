#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test functionality of coursera module.
"""

from __future__ import unicode_literals

import os.path
import unittest

from six import iteritems

from coursera.coursera import CourseraDownloader


class TestSyllabusParsing(unittest.TestCase):

    def setUp(self):
        """
        As setup, we mock some methods that would, otherwise, create
        repeatedly many web requests.

        More specifically, we mock:

        * the actual download of videos
        """

        self.dl = CourseraDownloader({})

        def get_page(url):
            """
            Mock function to prevent network requests.
            """
            return None

        self.dl.get_page = get_page

    def _assert_parse(self, filename, num_sections, num_lectures,
                      num_resources, num_videos):
        filename = os.path.join(
            os.path.dirname(__file__), "fixtures", "html",
            filename)

        with open(filename) as syllabus:
            lecture_page = syllabus.read()

            sections = self.dl.extract_sections(lecture_page)

            # section count
            self.assertEqual(len(sections), num_sections)

            # lecture count
            lectures = [lecture
                        for section in sections
                        for lecture in section["lectures"]]
            self.assertEqual(len(lectures), num_lectures)

            # resource count
            resources = [resource
                         for lecture in lectures
                         for resource in lecture["resources"]]

            # mp4 count
            self.assertEqual(
                sum(1 for resource in resources if resource['ext'] == "mp4"),
                num_videos)

    def test_parse(self):
        self._assert_parse(
            "regular-syllabus.html",
            num_sections=23,
            num_lectures=102,
            num_resources=502,
            num_videos=102)

    def test_links_to_wikipedia(self):
        self._assert_parse(
            "links-to-wikipedia.html",
            num_sections=5,
            num_lectures=37,
            num_resources=158,
            num_videos=36)

    def test_parse_preview(self):
        def _get_hidden_resources(lecture, lecture_url):
            lecture['resources'].append({
                'url': 'url',
                'name': 'name',
                'filename': 'video.mp4',
                'ext': 'mp4'
            })

        self.dl._get_hidden_resources = _get_hidden_resources

        self._assert_parse(
            "preview.html",
            num_sections=20,
            num_lectures=106,
            num_resources=106,
            num_videos=106)

    def test_get_hidden_resources(self):
        lecture_page_file = os.path.join(
            os.path.dirname(__file__), "fixtures", "html",
            "nlp-preview_lecture.html")
        f = open(lecture_page_file)
        with open(lecture_page_file) as f:
            lecture_page = f.read()

        def get_page(url):
            """
            Mock function to prevent network requests.
            """
            return lecture_page

        self.dl.get_page = get_page

        lecture = {
            "name": "",
            "resources": []
        }

        self.dl._get_hidden_resources(lecture, "")
        self.assertEqual(len(lecture["resources"]), 7)

    def test_sections_missed(self):
        self._assert_parse(
            "sections-not-to-be-missed.html",
            num_sections=9,
            num_lectures=61,
            num_resources=224,
            num_videos=61)

    def test_sections_missed2(self):
        self._assert_parse(
            "sections-not-to-be-missed-2.html",
            num_sections=20,
            num_lectures=121,
            num_resources=397,
            num_videos=121)

    def test_parse_classes_with_bs4(self):
        classes = {
            # issue 134, also downloads cloudfront.net links without ext
            'datasci-001': (10, 97, 360, 97),
            # issue 137
            'startup-001': (4, 44, 136, 44),
            # issue 131, also do not download forum links
            'wealthofnations-001': (8, 74, 296, 74),
            # issue 148
            'malsoftware-001': (3, 18, 56, 16)
        }

        for klass, counts in iteritems(classes):
            filename = "parsing-{0}-with-bs4.html".format(klass)
            self._assert_parse(
                filename,
                num_sections=counts[0],
                num_lectures=counts[1],
                num_resources=counts[2],
                num_videos=counts[3])

    def test_multiple_resources_with_the_same_format(self):
        self._assert_parse(
            "multiple-resources-with-the-same-format.html",
            num_sections=18,
            num_lectures=97,
            num_resources=478,
            num_videos=97)


if __name__ == "__main__":
    unittest.main()
