#!/usr/bin/env python

"""
Find settings for qutebrowser that are not present in local config
and vice versa.

1. Get the list of configurable settings from qutebrowser.
2. Parse local qutebrowser config file(s) and gather all present settings.
3. Compare the two lists.

Takes a list of config-files and/or config-file-directories
and parses all *.py-files.

It also takes commented out settings from the local config into account.
"""


import os
import sys
import argparse
import re
from pathlib import Path
from qutebrowser.config import configdata as qute_configdata
from qutebrowser.utils import standarddir as qute_standarddir


__title__ = 'qutebrowser-compare-config'
__description__ = ('Find settings for qutebrowser that are not present in '
                   'local config and vice versa.')
__copyright__ = "Copyright 2017, Fabio Rämi"
__author__ = 'Fabio Rämi'


def parse_arguments():
    """
    Parse all arguments.
    """
    def check_args():
        if args.missing and args.dropped:
            args.all = True
        elif not args.missing and not args.dropped:
            args.all = True
        else:
            args.all = False

        if not args.config:
            qute_standarddir._init_config(None)
            args.config_paths = [os.path.join(qute_standarddir.config(),
                                 'config.py')]
            if not os.path.isfile(args.config_paths[0]):
                print('No config file(s) provided and "{}" does not exist!'
                      .format(args.config_paths[0]),
                      file=sys.stderr)
                sys.exit(1)
        else:
            args.config_paths = [os.path.abspath(path) for path in args.config]

    parser = argparse.ArgumentParser(prog=__title__,
                                     description=__description__,
                                     formatter_class=argparse.
                                     RawDescriptionHelpFormatter)

    parser.add_argument('config', type=str, nargs='*',
                        default=[],
                        help='List of config files or directories')

    parser.add_argument('-m', '--missing', dest='missing',
                        action='store_true',
                        help='only list settings missing in local config')

    parser.add_argument('-d', '--dropped', dest='dropped',
                        action='store_true',
                        help='only list settings not present in '
                        'qutebrowser anymore')

    args = parser.parse_args()

    check_args()

    return args


def get_available_settings():
    qute_configdata.init()
    return [setting for setting in qute_configdata.DATA]


def get_relevant_string_from_config_line(line):
    match = re.search('(# )?c\.(?P<setting>.*) = .*', line)
    if match:
        return match.group('setting')


def parse_config_file(file):
    settings = []
    with open(file) as f:
        lines = [x.strip() for x in f.readlines()]
    for line in lines:
        if line:
            if not line.startswith('## '):
                setting = get_relevant_string_from_config_line(line)
                if setting:
                    settings.append(setting)
    return settings


def get_local_settings(config_paths):
    settings = []
    config_found = False
    for path in config_paths:
        if os.path.isdir(path):
            pathlist = Path(path).glob('**/*.py')
            for path in pathlist:
                config_found = True
                settings += parse_config_file(str(path))
        else:
            if path.endswith('.py') and os.path.isfile(path):
                config_found = True
                settings += parse_config_file(path)
    if config_found:
        return settings
    else:
        return False


def compare_lists(list1, list2):
    return list(set(list1) - set(list2))


def main():
    args = parse_arguments()
    qute_settings = get_available_settings()
    local_settings = get_local_settings(args.config_paths)
    if local_settings is False:
        print('No config file(s) found!', file=sys.stderr)
        sys.exit(1)
    not_local = compare_lists(qute_settings, local_settings)
    not_qute = compare_lists(local_settings, qute_settings)
    if args.all and not_local:
        print('####################\n'
              'Not in local config:\n'
              '####################')
    if args.all or args.missing:
        for setting in not_local:
            print(setting)
    if args.all and not_qute:
        if not_local:
            print()
        print('#############################\n'
              'Not available in qutebrowser:\n'
              '#############################')
    if args.all or args.dropped:
        for setting in not_qute:
            print(setting)


if __name__ == '__main__':
    main()
