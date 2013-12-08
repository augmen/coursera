# -*- coding: utf-8 -*-

"""
This module defines the global constants.
"""

import os

COURSE_URL = 'https://class.coursera.org/{course}'
HOME_URL = COURSE_URL + '/class/index'
LECTURE_URL = COURSE_URL + '/lecture/index'
AUTH_URL = COURSE_URL + "/auth/auth_redirector?type=login&subtype=normal"
LOGIN_URL = "https://accounts.coursera.org/api/v1/login"
ABOUT_URL =\
    "https://www.coursera.org/maestro/api/topic/information?topic-id={course}"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
