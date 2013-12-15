#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
For downloading lecture resources such as videos for Coursera classes. Given
a class name, username and password, it scrapes the course listing page to
get the section (week) and lecture names, and then downloads the related
materials into appropriately named files and directories.

Examples:
  coursera-dl -u <user> -p <passwd> saas
  coursera-dl -u <user> -p <passwd> -l listing.html -o saas --skip-download

For further documentation and examples, visit the project's home at:
  https://github.com/coursera-dl/coursera

Authors and copyright:
    © 2012-2013, John Lehmann (first last at geemail dotcom or @jplehmann)
    © 2012-2013, Rogério Brito (r lastname at ime usp br)
    © 2012-2013, Dirk Gorissen (first at geemail dotcom)
    © 2013, Jonas De Taeye (first dt at fastmail fm)

Contributions are welcome, but please add new unit tests to test your changes
and/or features.  Also, please try to make changes platform independent and
backward compatible.

Legalese:

 This program is free software: you can redistribute it and/or modify it
 under the terms of the GNU Lesser General Public License as published by
 the Free Software Foundation, either version 3 of the License, or (at your
 option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import unicode_literals

import argparse
import getpass
import logging
import os
import platform
import shutil
import sys
import tempfile
import time

import requests

from bs4 import BeautifulSoup
from six import iteritems, print_

import cookies
import downloaders
import _version

from define import ABOUT_URL, LECTURE_URL, PREVIEW_URL
from utils import *


class CourseraDownloader(object):
    """
    Class to download content (videos, lecture notes, ...) from coursera.org
    for use offline.

    Available options:

    preview:             If True, download preview videos.
    about:      Additionally download about metadata to about.json.
    reverse:             If True, download and save sections in reverse order.
    parser:              Html parser [html5lib html.parser lxml], see more at
                         http://www.crummy.com/software/BeautifulSoup/
                         bs4/doc/#installing-a-parser
    proxy:               HTTP/HTTPS proxy.
    hooks:               Hooks to run when finished.
    username:            Coursera username, not required for preview videos.
    password:            Coursera password, not required for preview videos.
    playlist:            Generate M3U playlist for every course section.
    sections:            List of section numbers to download.
    formats:             List of file extensions to download.
    skip_formats:        List of file extensions to skip.
    section_filter:      Only download the sections which match the regex.
    lecture_filter:      Only download the lectures which match the regex.
    resource_filter:     Only download the resources which match the regex.
    destination:         Download files to this location, default is pwd.
    output_template:     Output filename template.
    archive:             If True, tarball courses for archival storage.
    overwrite:           If True, overwrite already downloaded files.
    max_filename_length: Maximum length of filenames/directories in a path.
                         Default value is 90 for Windows, o.w. unlimited.
    wget:                Download with given wget binary.
    curl:                Download with given curl binary.
    aria2:               Download with given aria2 binary.
    axel:                Download with given axel binary.
    cookies:             File to read cookies from (skips authentication).
    lectures_page:       Uses/creates local cached version of lectures page.
    skip_download:       Do not download files.
    simulate:            Do not download the files and
                         do not write anything to disk.
    cache_dir:           Location in the filesystem where we can store
                         downloaded information permanently, set to None
                         to disable caching.
    """

    # How long to try to open a URL before timing out
    TIMEOUT = 30.0

    def __init__(self, params):
        self.params = params

        defaults = {
            'preview': False,
            'about': False,
            'reverse': False,
            'parser': 'html5lib',
            'proxy': None,
            'hooks': [],
            'username': None,
            'password': None,
            'playlist': False,
            'sections': [],
            'formats': [],
            'skip_formats': [],
            'section_filter': None,
            'lecture_filter': None,
            'resource_filter': None,
            'destination': None,
            'output_template': None,
            'archive': False,
            'overwrite': False,
            'max_filename_length': None,
            'wget': None,
            'curl': None,
            'aria2': None,
            'axel': None,
            'cookies': None,
            'lectures_page': None,
            'skip_download': None,
            'simulate': False,
            'cache_dir': None
        }
        for d in defaults:
            setattr(self, d, params.get(d, defaults[d]))

        # Linux max path length is typically around 4060 so assume that's ok
        if not self.max_filename_length and platform.system() == "Windows":
            self.max_filename_length = 120
            logging.info("Maximum filename length set to %s",
                         self.max_filename_length)

        if not self.output_template:
            self.output_template = "{section_index} {section_name}/" \
                                   "{lecture_index} {lecture_name} {name}{ext}"

        self.formats = [s.lower() for s in self.formats]
        self.skip_formats = [s.lower() for s in self.skip_formats]

        self.downloader = None
        self.session = None
        self.new_session()
    def new_session(self):
        self.session = requests.Session()

        #TODO: https
        if self.proxy:
            self.session.proxies = {'http': self.proxy}
        self.session.params['timeout'] = self.TIMEOUT

        self._downloader()

        return self.session

    def _downloader(self):
        """
        Decides which downloader to use.
        """

        external = {
            'wget': downloaders.WgetDownloader,
            'curl': downloaders.CurlDownloader,
            'aria2': downloaders.Aria2Downloader,
            'axel': downloaders.AxelDownloader,
        }

        for bin, klass in iteritems(external):
            if self.params.get(bin):
                self.downloader = klass(self.session,
                                        bin=self.params.get(bin))
                break

    def get_course_cookies(self, course):
        """
        Get the cookies for the given course, and add them to
        the current session.

        We do not validate the cookies if they are loaded from a cookies file
        because this is intended for debugging purposes or if the coursera
        authentication process has changed.

        Returns True if the cookies are retrieved successfully.
        """
        if self.cookies:
            cookie_jar = cookies.read_for_course(self.cookies, course)
            self.session.cookies.update(cookie_jar)
            logging.info('Loaded cookies from %s', self.cookies)
        else:
            if self.cache_dir:
                cached_cookies_file = os.path.join(
                    self.cache_dir,
                    'cookies_' + self.username + '.txt')
                cookie_jar = cookies.read(cached_cookies_file)
                self.session.cookies.update(cookie_jar)
                if cookies.validate_session(self.session, course):
                    logging.info('Already authenticated.')
                    return True

            ok = cookies.get_course_cookies(
                self.session, course,
                self.username, self. password)
            if not ok:
                return False

            if self.cache_dir:
                cookies.write(self.session.cookies, cached_cookies_file)

        return True

    def course_from_url(self, course_url):
        """Given the course URL, return the course name, e.g., algo2012-p2"""
        return course_url.split('/')[3]

    def lecture_url_from_course(self, course, preview=False):
        """Given the name of a course, return the lecture url"""
        if preview:
            return PREVIEW_URL.format(course=course)

        return LECTURE_URL.format(course=course)

    def get_response(self, url, retries=3, method="GET", **kwargs):
        """
        Get the response
        """
        kwargs.update(allow_redirects=True)
        for i in range(retries):
            try:
                r = self.session.request(method, url, **kwargs)
                r.raise_for_status()
            except Exception as e:
                logging.debug("Retrying to connect url: %s", url)
                pass
            else:
                return r

        raise e

    def get_headers(self, url):
        """
        Get the headers
        """
        r = self.get_response(url, method="HEAD")
        headers = r.headers
        r.close()
        return headers

    def get_page(self, url):
        """
        Get the content
        """
        r = self.get_response(url)
        page = r.content
        r.close()
        return page

    def get_json(self, url):
        """
        Get the json data
        """
        r = self.get_response(url)
        data = r.json()
        r.close()
        return data

    def get_sections(self, course_url):
        """
        Given the video lecture URL of the course, return a list of all
        sections, including lectures and resources
        """
        logging.info("* Collecting sections from %s", course_url)

        # get the course lecture page
        lecture_page = self.get_page(course_url)

        return self.extract_sections(lecture_page)

    def extract_sections(self, lecture_page):
        soup = BeautifulSoup(lecture_page, self.parser)

        # extract the sections
        section_headers = soup.findAll("div",
                                       {"class": "course-item-list-header"})
        sections = []

        for section_header in section_headers:
            # title of this section
            h3 = section_header.findNext('h3')
            assert h3 is not None, "couldn't find section"
            section = {
                'name': h3.text.strip(),
                'lectures': []
            }

            # get all the lectures for this section
            ul = section_header.next_sibling
            lecture_list = ul.findAll('li')

            for lecture_list_item in lecture_list:
                assert lecture_list_item.a is not None, "couldn't get lecture"
                lecture = {
                    'name': lecture_list_item.a.find(text=True).strip(),
                    'time': None,
                    'resources': []
                }

                # collect all the resources for this lecture (ppt, mp4, ...)
                lecture_resources = lecture_list_item.find(
                    'div', {'class': 'course-lecture-item-resource'})
                resource_links = lecture_resources.findAll('a') \
                    if lecture_resources else []

                for resource_link in resource_links:
                    resource_url = clean_url(resource_link.get('href'))
                    if not resource_url:
                        continue
                    resource = {
                        'url': resource_url,
                        'name': resource_link.get('title', '').strip(),
                        # for simulation purposes, we use the http headers
                        # for the actual downloading
                        'filename': resource_filename_from_url(resource_url)
                    }
                    _, resource['ext'] = path.splitext(resource['filename'])
                    resource['ext'] = resource['ext'].lstrip('.')

                    # Sometimes the raw, uncompressed source videos are
                    # available as well. Don't download them as they are huge
                    # and available in compressed form anyway.
                    if resource['url'].find('source_videos') > 0:
                        logging.info("will skip raw source video %s",
                                     resource['url'])
                    else:
                        # Skip files without extension if they are not
                        # served from cloudfront.net. For instance, some
                        # courses add links to wikipedia, forum, ... .
                        if resource['ext'] or "cloudfront.net" in resource_url:
                            lecture['resources'].append(resource)

                # Check if the video is included in the resources, if not, try
                # to download it via the modal window.
                # Preview pages do not have resources, so in that case we also
                # use the modal window.
                if not any(r['ext'] == "mp4" for r in lecture['resources']):
                    lecture_link = lecture_list_item.find(
                        'a', {'class': 'lecture-link'})
                    if not lecture_link.has_attr('data-modal-iframe'):
                        continue

                    lecture_url = clean_url(lecture_link['data-modal-iframe'])
                    logging.info('Lecture "%s" has hidden resources',
                                 lecture['name'])
                    self._get_hidden_resources(lecture, lecture_url)

                section['lectures'].append(lecture)

            sections.append(section)

        return sections

    def _get_hidden_resources(self, lecture, lecture_url):
        try:
            page = self.get_page(lecture_url)
            bb = BeautifulSoup(page, self.parser)
            vobj = bb.find('source', type="video/mp4")

            if not vobj:
                logging.warning(
                    "Warning: Failed to find video for %s",
                    lecture['name'])
            else:
                resource = {
                    'url': clean_url(vobj['src']),
                    'name': lecture['name'].strip(),
                    'filename': 'video.mp4',
                    'ext': 'mp4'
                }
                lecture['resources'].append(resource)
                subtitle_tracks = bb.findAll(
                    'track', {'kind': 'subtitles'}) or []

                for subtitle_track in subtitle_tracks:
                    lang = subtitle_track.get('srclang').strip()
                    resource = {
                        'url': clean_url(subtitle_track['src']),
                        'name': 'Subtitles ' + lang,
                        'filename': 'Subtitles ' + lang + '.srt',
                        'ext': 'srt'
                    }
                    lecture['resources'].append(resource)
        except requests.exceptions.HTTPError as e:
            # sometimes there is a lecture without a video (e.g.,
            # genes-001) so this can happen.
            logging.warning("Warning: failed to open the direct"
                            " video link %s: %s",
                            resource['url'], e)

    def _download(self, url, filepath):
        try:
            response = self.get_response(url, stream=True)
            full_size = response.headers.get('content-length')
            done_size = 0
            slice_size = 524288  # 512KB buffer
            last_time = time.time()
            with open(filepath, 'wb') as f:
                for data in response.iter_content(slice_size):
                    f.write(data)
                    try:
                        percent = int(float(done_size) / full_size * 100)
                    except:
                        percent = 0
                    try:
                        cur_time = time.time()
                        speed = float(slice_size) / float(
                            cur_time - last_time)
                        last_time = cur_time
                    except:
                        speed = 0
                    if speed < 1024:
                        speed_str = '{:.1f} B/s'.format(speed)
                    elif speed < 1048576:
                        speed_str = '{:.1f} KB/s'.format(speed / 1024)
                    else:
                        speed_str = '{:.1f} MB/s'.format(speed / 1048576)
                    status_str = 'status: {:2d}% {}'.format(
                        percent, speed_str)
                    sys.stdout.write(
                        status_str + ' ' * (25 - len(status_str)) + '\r')
                    sys.stdout.flush()
                    done_size += slice_size
            response.close()
            sys.stdout.write(' ' * 25 + '\r')
            sys.stdout.flush()
        except Exception as e:
            logging.error(e)
            return False
        return True


def parse_args():
    """Parse the command line arguments/options.
    """

    parser = argparse.ArgumentParser(
        prog='coursera-dl',
        description="""Coursera-dl is a python package for downloading
        course videos and resources available at coursera.org.
        """,
        add_help=False,
        formatter_class=HelpFormatter)

    positional = parser.add_argument_group('Positional arguments')
    general = parser.add_argument_group('General options')
    authentication = parser.add_argument_group('Authentication options')
    filter = parser.add_argument_group('Filter options')
    filesystem = parser.add_argument_group('Filesystem options')
    download = parser.add_argument_group('Download options')
    debugging = parser.add_argument_group('Debugging / Verbosity options')

    # Positional argument
    positional.add_argument('course',
                            nargs='+',
                            help="""one or more courses to download, use the
                                 identifier from the course URL:
                                 https://class.coursera.org/<course>""")

    # General Options
    general.add_argument('-h',
                         '--help',
                         action='help',
                         help='show this help message and exit')
    general.add_argument('--version',
                         action='version',
                         version=_version.__version__)
    general.add_argument('--preview',
                         dest='preview',
                         action='store_true',
                         default=False,
                         help='download preview videos instead'
                              ' of the regular course material')
    general.add_argument('--about',
                         dest='about',
                         action='store_true',
                         default=False,
                         help='additionally download about metadata to'
                              ' about.json')
    general.add_argument('-r',
                         '--reverse',
                         dest='reverse',
                         action='store_true',
                         default=False,
                         help='download and save sections in reverse order')
    general.add_argument('--parser',
                         dest='parser',
                         type=str,
                         default='html5lib',
                         help='html parser to use, one of [html5lib'
                              ' html.parser lxml] (default: html5lib)')
    general.add_argument('--proxy',
                         dest='proxy',
                         metavar='URL',
                         default=None,
                         help='use the specified HTTP/HTTPS proxy')
    general.add_argument('--hooks',
                         dest='hooks',
                         action='append',
                         default=[],
                         help='hooks to run when finished')
    general.add_argument('--playlist',
                         dest='playlist',
                         action='store_true',
                         default=False,
                         help='generate M3U playlist for every course section')

    # Authentication Options
    authentication.add_argument('-u',
                                '--username',
                                dest='username',
                                action='store',
                                default=None,
                                help='coursera username')
    authentication.add_argument('-p',
                                '--password',
                                dest='password',
                                action='store',
                                default=None,
                                help='coursera password')
    authentication.add_argument('-n',
                                '--netrc',
                                metavar='FILE',
                                dest='netrc',
                                nargs='?',
                                action=FullPath,
                                const=True,
                                default=None,
                                help='use netrc for reading passwords, uses '
                                     'default location if no file specified')

    # Filtering Options
    filter.add_argument('--sections',
                        metavar='NUMBERS',
                        dest='sections',
                        default='',
                        help='space separated list of section numbers'
                             ' to download, e.g. "1 3 8"')
    filter.add_argument('-f',
                        '--formats',
                        metavar='EXTENSIONS',
                        dest='formats',
                        action='store',
                        default='',
                        help='space separated list of file extensions'
                             ' to download, e.g "mp4 pdf"')
    filter.add_argument('--skip-formats',
                        dest='skip_formats',
                        metavar='EXTENSIONS',
                        default='',
                        help='space separated list of file extensions to skip,'
                             ' e.g., "ppt srt pdf"')
    filter.add_argument('-sf',
                        '--section-filter',
                        metavar='REGEX',
                        dest='section_filter',
                        action='store',
                        default=None,
                        help='only download sections which contain this'
                             ' regex (default: disabled)')
    filter.add_argument('-lf',
                        '--lecture-filter',
                        metavar='REGEX',
                        dest='lecture_filter',
                        action='store',
                        default=None,
                        help='only download lectures which contain this regex'
                             ' (default: disabled)')
    filter.add_argument('-rf',
                        '--resource-filter',
                        metavar='REGEX',
                        dest='resource_filter',
                        action='store',
                        default=None,
                        help='only download resources which match this regex'
                             ' (default: disabled)')

    # Filesystem Options
    filesystem.add_argument('-d',
                            '--destination',
                            metavar='DIR',
                            dest='destination',
                            type=str,
                            default=".",
                            action=FullPath,
                            help='download everything to the given directory,'
                                 ' defaults to current directory')
    filesystem.add_argument('-o',
                            '--output',
                            metavar='TEMPLATE',
                            dest='output_template',
                            type=str,
                            default="",
                            help="""output filename template. Use one
                                 or more of the following fields:\n
                                 - {name}: resource name\n
                                 - {ext}: resource ext\n
                                 - {filename}: resource filename
                                 (includes ext)\n
                                 - {section_index}: position in section list\n
                                 - {section_name}: section name\n
                                 - {lecture_index}: position in lecture list\n
                                 - {lecture_name}: lecture name
                                 """)
    filesystem.add_argument('--archive',
                            dest='archive',
                            action='store_true',
                            default=False,
                            help='tarball courses for archival storage')
    filesystem.add_argument('--overwrite',
                            dest='overwrite',
                            action='store_true',
                            default=False,
                            help='overwrite already downloaded files')
    filesystem.add_argument('--max-filename-length',
                            metavar="NUMBER",
                            dest='max_filename_length',
                            type=int,
                            default=None,
                            help='maximum length of filenames/directories'
                                 ' in a path (windows only)')

    # Download Options
    download.add_argument('--wget',
                          metavar='BIN',
                          dest='wget',
                          action='store',
                          nargs='?',
                          const='wget',
                          default=None,
                          help='download using wget')
    download.add_argument('--curl',
                          metavar='BIN',
                          dest='curl',
                          action='store',
                          nargs='?',
                          const='curl',
                          default=None,
                          help='download using curl')
    download.add_argument('--aria2',
                          metavar='BIN',
                          dest='aria2',
                          action='store',
                          nargs='?',
                          const='aria2c',
                          default=None,
                          help='download using aria2')
    download.add_argument('--axel',
                          metavar='BIN',
                          dest='axel',
                          action='store',
                          nargs='?',
                          const='axel',
                          default=None,
                          help='download using axel')

    # Debugging Options
    debugging.add_argument('--cookies',
                           dest='cookies',
                           action='store',
                           default=None,
                           help='file to read cookies from')
    debugging.add_argument('--lectures-page',
                           metavar='FILE',
                           dest='lectures_page',
                           help='uses/creates local cached version of'
                                ' lectures page')
    debugging.add_argument('--skip-download',
                           dest='skip_download',
                           action='store_true',
                           default=False,
                           help='do not download files')
    debugging.add_argument('-s',
                           '--simulate',
                           dest='simulate',
                           action='store_true',
                           default=False,
                           help='do not download the files and'
                                ' do not write anything to disk')
    debugging.add_argument('--debug',
                           dest='debug',
                           action='store_true',
                           default=False,
                           help='print lots of debug information')
    debugging.add_argument('--quiet',
                           dest='quiet',
                           action='store_true',
                           default=False,
                           help='omit as many messages as possible'
                                ' (only printing errors)')
    debugging.add_argument('--cache-dir',
                           metavar='DIR',
                           dest='cache_dir',
                           action=FullPath,
                           default=None,
                           help="""location in the filesystem where %(prog)s
                                can store downloaded information permanently,
                                the default location is /tmp""")
    debugging.add_argument('--no-cache-dir',
                           dest='no_cache_dir',
                           action='store_true',
                           default=False,
                           help='disable filesystem caching')
    debugging.add_argument('--clear-cache',
                           dest='clear_cache',
                           action='store_true',
                           default=False,
                           help='clear cached cookies')

    # decode arguments
    return parser.parse_args(
        [arg.decode(sys.stdin.encoding) for arg in sys.argv[1:]])


def validate_args(args):
    """Validate and sanitize the command line arguments/options, fail fast.
    """

    # Check the parser
    if args.parser == "html.parser" and sys.version_info < (2, 7, 3):
        logging.warning("Warning: 'html.parser' may cause problems"
                        " on Python < 2.7.3")
    if args.parser not in ['html5lib', 'html.parser', 'lxml']:
        logging.error("Invalid parser: '%s',"
                      " choose from 'html5lib', 'html.parser', 'lxml'",
                      args.parser)
        sys.exit(1)

    # Check if sections is a list of integers
    try:
        args.sections = [int(x) for x in args.sections.split()]
    except Exception as e:
        logging.error("Invalid sections list, this should be a"
                      " list of integers.")
        sys.exit(1)

    # Split string of extensions, remove prefixing dot if there is one
    args.formats = [s.lstrip('.') for s in args.formats.split()]
    args.skip_formats = [s.lstrip('.') for s in args.skip_formats.split()]

    # We do not need the username/password if a cookies file is specified
    if args.cookies:
        if not os.path.exists(args.cookies):
            logging.error("Cookies file not found: %s", args.cookies)
            sys.exit(1)
    # We don't need credentials to download preview videos
    elif not args.preview:
        if args.netrc:
            credentials = netrc_credentials(
                None if args.netrc is True else args.netrc)
            if credentials is None:
                logging.error("No credentials found in .netrc file")
                sys.exit(1)
            logging.info("Credentials found in .netrc file")
            args.username = credentials[0]
            args.password = credentials[1]
        else:
            if not args.username:
                logging.error('Please provide a username with the -u option, '
                              'or a .netrc file with the -n option.')
                sys.exit(1)
            if not args.password:
                args.password = getpass.getpass(
                    'Coursera password for {0}: '.format(args.username))

    if args.no_cache_dir:
        args.cache_dir = None
    else:
        if not args.cache_dir:
            # define a per-user cache folder
            if os.name == "posix":
                import pwd
                user = pwd.getpwuid(os.getuid())[0]
            else:
                user = getpass.getuser()

            args.cache_dir = os.path.join(tempfile.gettempdir(),
                                          user + "_coursera-dl_cache")

        mkdir_p(args.cache_dir, 0o700)
        if args.clear_cache:
            shutil.rmtree(args.cache_dir)
            mkdir_p(args.cache_dir, 0o700)

        logging.debug("Cache dir: %s", args.cache_dir)

    return args


def logging_config(format, level):
    """Like logging.basicConfig, but with custom Formatter/Filter."""

    root = logging.getLogger()
    if len(root.handlers) == 0:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(IndentingFormatter(format))
        root.addHandler(handler)
        root.addFilter(CountingFilter())
        root.setLevel(level)


def indent(step=1):
    root = logging.getLogger()
    if len(root.handlers):
        root.handlers[0].formatter.indent(step)


def main():
    args = parse_args()

    # Initialize the logging system first so that other functions
    # can use it right away
    if args.debug:
        logging_config(level=logging.DEBUG,
                       format='%(name)s[%(funcName)s] %(message)s')
    elif args.quiet:
        logging_config(level=logging.ERROR,
                       format='%(name)s: %(message)s')
    else:
        logging_config(level=logging.INFO,
                       format='%(indentation)s%(message)s')

    args = validate_args(args)

    logging.info("Coursera-dl v%s (%s)", _version.__version__, args.parser)

    # Instantiate the downloader class
    d = CourseraDownloader(vars(args))

if __name__ == '__main__':
    main()
