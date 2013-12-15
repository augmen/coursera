# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
import os
import requests
import subprocess


class Downloader(object):
    """
    Base downloader class.

    Every subclass should implement the _start_download method.
    """

    def _start_download(self, url, filename):
        """
        Actual method to download the given url to the given file.
        This method should be implemented by the subclass.
        """
        raise NotImplementedError("Subclasses should implement this")

    def download(self, url, filename):
        """
        Download the given url to the given file. When the download
        is aborted by the user, the partially downloaded file is also removed.
        """

        try:
            return self._start_download(url, filename)
        except KeyboardInterrupt as e:
            logging.info(
                'Keyboard Interrupt -- Removing partial file: %s', filename)
            try:
                os.remove(filename)
            except OSError:
                pass
            raise e


class ExternalDownloader(Downloader):
    """
    Downloads files with an external downloader.

    We could possibly use python to stream files to disk,
    but this is slow compared to these external downloaders.

    :param session: Requests session.
    :param bin: External downloader binary.
    """

    # External downloader binary
    bin = None

    def __init__(self, session, bin=None):
        self.session = session
        self.bin = bin or self.__class__.bin

        if not self.bin:
            raise RuntimeError("No bin specified")

    def _prepare_cookies(self, command, url):
        """
        Extract cookies from the requests session and add them to the command
        """

        req = requests.models.Request()
        req.method = 'GET'
        req.url = url

        cookie_values = requests.cookies.get_cookie_header(
            self.session.cookies, req)

        if cookie_values:
            self._add_cookies(command, cookie_values)

    def _add_cookies(self, command, cookie_values):
        """
        Add the given cookie values to the command
        """

        raise RuntimeError("Subclasses should implement this")

    def _create_command(self, url, filename):
        """
        Create command to execute in a subprocess.
        """
        raise NotImplementedError("Subclasses should implement this")

    def _start_download(self, url, filename):
        command = self._create_command(url, filename)
        self._prepare_cookies(command, url)
        logging.debug('Executing %s: %s', self.bin, command)
        try:
            returncode = subprocess.call(command)
        except OSError as e:
            msg = "{0}. Are you sure that '{1}' is the right bin?".format(
                e, self.bin)
            raise OSError(msg)
        return returncode == 0


class WgetDownloader(ExternalDownloader):
    """
    Uses wget, which is robust and gives nice visual feedback.
    """

    bin = 'wget'

    def _add_cookies(self, command, cookie_values):
        command.extend(['--header', "Cookie: " + cookie_values])

    def _create_command(self, url, filename):
        return [self.bin, url, '-O', filename, '--no-cookies',
                '--no-check-certificate']


class CurlDownloader(ExternalDownloader):
    """
    Uses curl, which is robust and gives nice visual feedback.
    """

    bin = 'curl'

    def _add_cookies(self, command, cookie_values):
        command.extend(['--cookie', cookie_values])

    def _create_command(self, url, filename):
        return [self.bin, url, '-k', '-#', '-L', '-o', filename]


class Aria2Downloader(ExternalDownloader):
    """
    Uses aria2. Unfortunately, it does not give a nice visual feedback, but
    gets the job done much faster than the alternatives.
    """

    bin = 'aria2c'

    def _add_cookies(self, command, cookie_values):
        command.extend(['--header', "Cookie: " + cookie_values])

    def _create_command(self, url, filename):
        return [self.bin, url, '-o', filename,
                '--check-certificate=false', '--log-level=notice',
                '--max-connection-per-server=4', '--min-split-size=1M']


class AxelDownloader(ExternalDownloader):
    """
    Uses axel, which is robust and it both gives nice
    visual feedback and get the job done fast.
    """

    bin = 'axel'

    def _add_cookies(self, command, cookie_values):
        command.extend(['-H', "Cookie: " + cookie_values])

    def _create_command(self, url, filename):
        return [self.bin, '-o', filename, '-n', '4', '-a', url]
