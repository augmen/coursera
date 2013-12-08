#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse


class HelpFormatter(argparse.HelpFormatter):
    """Help message formatter which print the optional argument value
    only once, i.e.
        -s, --long ARGS
    instead of
        -s ARGS, --long ARGS
    Makes left column 32 characters wide.
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
