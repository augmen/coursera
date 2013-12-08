# -*- coding: utf-8 -*-

"""
This module defines the global constants.
"""

import os
import getpass
import tempfile

COURSE_URL = 'https://class.coursera.org/%s'
HOME_URL = COURSE_URL + '/class/index'
LECTURE_URL = COURSE_URL + '/lecture/index'
AUTH_URL = COURSE_URL + "/auth/auth_redirector?type=login&subtype=normal"
LOGIN_URL = "https://accounts.coursera.org/api/v1/login"
ABOUT_URL =\
    "https://www.coursera.org/maestro/api/topic/information?topic-id=%s"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# define a per-user cache folder
if os.name == "posix":
    import pwd
    user = pwd.getpwuid(os.getuid())[0]
else:
    user = getpass.getuser()

CACHE_PATH = os.path.join(tempfile.gettempdir(), user+"_coursera_dl_cache")
COOKIES_PATH = os.path.join(CACHE_PATH, 'cookies')
