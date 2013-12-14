# -*- coding: utf-8 -*-

"""
Cookie handling module.
"""

from __future__ import unicode_literals

import logging

import requests

from six.moves import StringIO
from six.moves import http_cookiejar as cookielib

from define import LOGIN_URL, COURSE_URL, AUTH_URL


# Monkey patch cookielib.Cookie.__init__.
# Reason: The expires value may be a decimal string,
# but the Cookie class uses int() ...
__orginal_init__ = cookielib.Cookie.__init__


def __fixed_init__(self, version, name, value,
                   port, port_specified,
                   domain, domain_specified, domain_initial_dot,
                   path, path_specified,
                   secure,
                   expires,
                   discard,
                   comment,
                   comment_url,
                   rest,
                   rfc2109=False,
                   ):
    if expires is not None:
        expires = float(expires)
    __orginal_init__(self, version, name, value,
                     port, port_specified,
                     domain, domain_specified, domain_initial_dot,
                     path, path_specified,
                     secure,
                     expires,
                     discard,
                     comment,
                     comment_url,
                     rest,
                     rfc2109=False,)

cookielib.Cookie.__init__ = __fixed_init__


def load(cookies_file):
    """
    Load cookies file into cookielib.MozillaCookieJar.
    """
    cj = cookielib.MozillaCookieJar()
    # loads the cookies file.
    # We pre-pend the file with the special Netscape header because the cookie
    # loader is very particular about this string.
    f = StringIO()
    f.write('# Netscape HTTP Cookie File')
    f.write(open(cookies_file, 'rU').read())
    f.flush()
    f.seek(0)

    # nasty hack: cj.load() requires a filename not a file, but if I use
    # stringio, that file doesn't exist. I used NamedTemporaryFile before,
    # but encountered problems on Windows.
    cj._really_load(f, 'StringIO.cookies', False, False)

    return cj


def read(cookies_file):
    """
    Read cookies file into RequestsCookieJar.
    """
    cj = requests.cookies.RequestsCookieJar()
    try:
        cached_cj = load(cookies_file)
        for cookie in cached_cj:
            cj.set_cookie(cookie)
        logging.debug('Loaded cookies from %s', cookies_file)
    except IOError:
        pass

    return cj


def write(cj, cookies_file):
    """
    Saves the RequestsCookieJar to disk in the Mozilla cookies.txt file
    format. We use this to prevents us from repeated authentications on the
    accounts.coursera.org and class.coursera.org/course sites.
    """
    cached_cj = cookielib.MozillaCookieJar()
    for cookie in cj:
        cached_cj.set_cookie(cookie)
    cached_cj.save(cookies_file)


def read_for_course(cookies_file, course):
    """
    Return a RequestsCookieJar containing the cookies for
    .coursera.org and class.coursera.org found in the given cookies_file.
    """

    path = "/" + course

    def cookies_filter(c):
        return c.domain == ".coursera.org" \
            or (c.domain == "class.coursera.org" and c.path == path)

    cj = load(cookies_file)

    new_cj = requests.cookies.RequestsCookieJar()
    for c in filter(cookies_filter, cj):
        new_cj.set_cookie(c)

    return new_cj


def get_login_cookies(session, course, username, password):
    """
    Login on accounts.coursera.org with the given credentials.
    This adds the following cookies to the session:
        sessionid, maestro_login, maestro_login_flag

    Returns True if login was successful.
    """

    try:
        session.cookies.clear('.coursera.org')
    except KeyError:
        pass

    # Hit course url to obtain csrf_token
    course_url = COURSE_URL.format(course=course)
    r = requests.get(course_url, allow_redirects=False)

    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(e)
        logging.error('Could not find course: %s', course)
        return False

    csrftoken = r.cookies.get('csrf_token')

    if not csrftoken:
        logging.error('Failed to find csrf cookie.')
        return False

    # Now make a call to the authenticator url.
    headers = {
        'Cookie': 'csrftoken=' + csrftoken,
        'Referer': 'https://accounts.coursera.org/signin',
        'X-CSRFToken': csrftoken,
    }

    data = {
        'email': username,
        'password': password
    }

    r = session.post(LOGIN_URL, data=data,
                     headers=headers, allow_redirects=False)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        logging.error('Cannot login on accounts.coursera.org: %s', r.text)
        return False

    # Check if we managed to login
    if 'CAUTH' not in session.cookies:
        raise logging.error("Failed to authenticate as %s", username)
        return False

    logging.info('Logged in on accounts.coursera.org.')
    return True


def get_course_cookies(session, course, username, password):
    """
    Get the necessary cookies to authenticate on class.coursera.org.

    To access the class pages we need two cookies on class.coursera.org:
        csrf_token, session
    """

    # First, check if we already have the .coursera.org cookies.
    if session.cookies.get('CAUTH', domain=".coursera.org"):
        logging.debug('Already logged in on accounts.coursera.org.')
    else:
        success = get_login_cookies(session, course, username, password)
        if not success:
            return False

    try:
        session.cookies.clear('class.coursera.org', '/' + course)
    except KeyError:
        pass

    # Authenticate on class.coursera.org
    auth_url = AUTH_URL.format(course=course)
    r = session.get(auth_url)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        logging.error('Cannot login on class.coursera.org: %s', r.text)
        return False

    if not has_course_cookies(session.cookies, course):
        logging.error('Did not find necessary cookies.')
        return False

    logging.info('Found authentication cookies.')
    return True


def has_course_cookies(cj, course):
    """
    Checks whether we have all the required cookies
    to authenticate on class.coursera.org.
    """
    domain = 'class.coursera.org'
    path = "/" + course

    return cj.get('csrf_token', domain=domain, path=path) is not None


def validate_session(session, course):
    """
    Checks whether we have all the required cookies
    to authenticate on class.coursera.org. Also check for and remove
    stale session cookies.
    """
    if not has_course_cookies(session.cookies, course):
        return False

    url = COURSE_URL.format(course=course) + '/class'
    r = session.head(url, allow_redirects=False)

    if r.status_code == 200:
        return True
    else:
        logging.debug('Stale session.')
        try:
            session.cookies.clear('.coursera.org')
        except KeyError:
            pass
        return False
