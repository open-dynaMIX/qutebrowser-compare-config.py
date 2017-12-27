#!/usr/bin/env python

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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


import sys
import argparse
import re
from pathlib import Path
from qutebrowser.config import configdata as qute_configdata
from qutebrowser.utils import standarddir as qute_standarddir


__title__ = 'qutebrowser-compare-config.py'
__description__ = ('Find settings for qutebrowser that are not present in '
                   'local config and vice versa.')
__copyright__ = "Copyright 2017, Fabio Rämi"
__license__ = "GPL"
__author__ = 'Fabio Rämi'


def parse_arguments():
    """
    Parse all arguments.
    """
    def check_args():
        """
        Check what to do and set args.all variable.
        """
        if args.missing and args.dropped:
            args.all = True
        elif not args.missing and not args.dropped:
            args.all = True
        else:
            args.all = False

    def handle_path(path):
        """
        Handle single path from args.config.
        Resolve all relative paths and gather all paths from directories.
        """
        p = Path(path).resolve()
        if not p.exists():
            print('"{}" does not exist!'.format(str(p)),
                  file=sys.stderr)
            sys.exit(1)
        elif p.is_file():
            args.config_paths.append(p.resolve())
        else:
            for path in list(p.glob('**/*.py')):
                handle_path(path)

    def handle_paths():
        """
        Handle config-paths from args.config.
        """
        if not args.config:
            qute_standarddir._init_config(None)
            args.config_paths = [Path(qute_standarddir.config(), 'config.py')]
            if not args.config_paths[0].is_file():
                print('No config file(s) provided and "{}" does not exist!'
                      .format(args.config_paths[0]),
                      file=sys.stderr)
                sys.exit(1)
        else:
            args.config_paths = []
            for path in args.config:
                handle_path(path)
            args.config_paths = list(set(args.config_paths))

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
    handle_paths()

    return args


def get_available_settings():
    """
    Get all available settings from qutebrowser.
    return: list of strings
    """
    qute_configdata.init()
    return [setting for setting in qute_configdata.DATA]


def get_relevant_string_from_config_line(line):
    """
    Get setting name from config-line.
    return: string if found, else None
    """
    match = re.search('(#( )?)?c\.(?P<setting>.*) = .*', line)
    if match:
        return match.group('setting')


def parse_config_file(path):
    """
    Parse a single config-file.
    """
    settings = []
    with path.open() as f:
        lines = [x.strip() for x in f.readlines()]
    for line in lines:
        setting = get_relevant_string_from_config_line(line)
        if setting:
            settings.append(setting)
    return settings


def get_local_settings(config_paths):
    """
    Parse all given config-files for settings.
    return: list of strings
    """
    settings = []
    for path in config_paths:
        settings += parse_config_file(path)
    return settings


def compare_lists(list1, list2):
    """
    Compare two lists.
    return: list of entries from list1 that are not in list2
    """
    return list(set(list1) - set(list2))


def main():
    """
    main
    """
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
