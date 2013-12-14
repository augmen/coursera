# -*- coding: utf-8 -*-

"""
This module provides utility functions that are used within the script.
"""

from __future__ import unicode_literals

import argparse
import errno
import logging
import netrc
import os
import platform
import re

from os import path

class HelpFormatter(argparse.HelpFormatter):
    """Help message formatter which print the optional argument value
    only once, i.e.
        -s, --long ARGS
    instead of
        -s ARGS, --long ARGS
    Makes left column 32 characters wide.
    Allow action descriptions to use \n.
    """
    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=24,
                 width=None):

        argparse.HelpFormatter.__init__(self,
                                        prog,
                                        indent_increment=indent_increment,
                                        max_help_position=32,
                                        width=width)

        self._whitespace_matcher = re.compile(r'[ \t\r\f\v]+')

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar

        else:
            options_string = ', '.join(action.option_strings)

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                return options_string
            # if the Optional takes a value, format is:
            #    -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)

                return '{} {}'.format(options_string, args_string)

    def _split_lines(self, text, width):
        """Allow description to be split with \n, but keep the text wrapping
        """
        text = self._whitespace_matcher.sub(' ', text).strip()
        return [l for line in text.split("\n\n")
                for l in argparse._textwrap.wrap(
                    line.strip().replace("\n", ""), width)]


class FullPath(argparse._StoreAction):
    """Expand user- and relative-paths"""
    def __call__(self, parser, namespace, values, option_string=None):
        if isinstance(values, string_types):
            values = path.abspath(path.expanduser(values))
        setattr(namespace, self.dest, values)


class IndentingFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        self.indentation = 0

    def indent(self, step=1):
        self.indentation = max(self.indentation + step, 0)

    def format(self, record):
        indentation = ""
        if self.indentation:
            indentation = 2 * self.indentation * " " + "- "

        record.__dict__['indentation'] = indentation
        return logging.Formatter.format(self, record)



def netrc_paths():
    """
    Returns a list of config files paths to try in order, given config file
    name and possibly a user-specified path.

    For Windows platforms, there are several paths that can be tried to
    retrieve the netrc file. There is, however, no "standard way" of doing
    things.

    A brief recap of the situation (all file paths are written in Unix
    convention):

    1. By default, Windows does not define a $HOME path. However, some
    people might define one manually, and many command-line tools imported
    from Unix will search the $HOME environment variable first. This
    includes MSYSGit tools (bash, ssh, ...) and Emacs.

    2. Windows defines two 'user paths': $USERPROFILE, and the
    concatenation of the two variables $HOMEDRIVE and $HOMEPATH. Both of
    these paths point by default to the same location, e.g.
    C:\\Users\\Username

    3. $USERPROFILE cannot be changed, however $HOMEDRIVE and $HOMEPATH
    can be changed. They are originally intended to be the equivalent of
    the $HOME path, but there are many known issues with them

    4. As for the name of the file itself, most of the tools ported from
    Unix will use the standard '.dotfile' scheme, but some of these will
    instead use "_dotfile". Of the latter, the two notable exceptions are
    vim, which will first try '_vimrc' before '.vimrc' (but it will try
    both) and git, which will require the user to name its netrc file
    '_netrc'.

    Relevant links :
    http://markmail.org/message/i33ldu4xl5aterrr
    http://markmail.org/message/wbzs4gmtvkbewgxi
    http://stackoverflow.com/questions/6031214/

    Because the whole thing is a mess, I suggest we tried various sensible
    defaults until we succeed or have depleted all possibilities.
    """

    if platform.system() == 'Windows':
        # where could the netrc file be hiding, try a number of places
        env_vars = ["HOME", "HOMEDRIVE",
                    "HOMEPATH", "USERPROFILE", "SYSTEMDRIVE"]
        env_dirs = [os.environ[e] for e in env_vars if os.environ.get(e, None)]

        # also try the root/cur dirs
        env_dirs += ["C:", ""]

        # possible filenames
        file_names = [".netrc", "_netrc"]

        # all possible paths
        paths = [os.path.join(dir, fn)
                 for dir in env_dirs
                 for fn in file_names]
    else:
        # on *nix just put None, and the correct default will be used
        paths = [None]

    return paths


def netrc_credentials(path=None):
    """
    Read username/password from the users' netrc file. Returns None if no
    coursera-dl credentials can be found.
    """

    paths = [path] if path else netrc_paths()
    credentials = None

    # try the paths one by one and return the first one that works
    for p in paths:
        try:
            logging.debug('Search credentials in netrc file %s', path)
            auths = netrc.netrc(p).authenticators('coursera-dl')
            credentials = (auths[0], auths[2])
            break
        except (IOError, TypeError, netrc.NetrcParseError) as e:
            pass

    return credentials


def mkdir_p(path, mode=0o777):
    """
    Create subdirectory hierarchy given in the paths argument.
    """

    try:
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
def clean_url(url):
    """
    Strip whitespace characters from the beginning and the end of the url
    and add a default scheme.
    """

    if url is None:
        return None

    url = url.strip()

    if url and not urlparse(url).scheme:
        url = "http://" + url

    return url


