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

This will not try to resolve the found issues. Your config files will only be
read, never written to.
"""


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
    def check_what_to_do():
        """
        Check what to do and set args.all.
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

        Appends them as pathlib.Path to args.config_paths.

        Args:
            path: The path to be handled (str)
        """
        p = Path(path).resolve()
        if not p.exists():
            parser.error('"{}" does not exist!'.format(str(p)))
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
                parser.error('No config file(s) provided and "{}" does not '
                             'exist!'.format(args.config_paths[0]))
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
                        help='List of config files or directories. '
                        'Defaults to standard location of config.py')

    parser.add_argument('-m', '--missing', dest='missing',
                        action='store_true',
                        help='only list settings missing in local config')

    parser.add_argument('-d', '--dropped', dest='dropped',
                        action='store_true',
                        help='only list settings not present in '
                        'qutebrowser')

    parser.add_argument('-n', '--naked', dest='naked',
                        action='store_true',
                        help='omit additional information '
                        '(file/line-number/URL')

    args = parser.parse_args()

    check_what_to_do()
    handle_paths()

    return args


def get_available_settings():
    """
    Get all available settings from qutebrowser.

    Return:
        List of settings [str, ...]
    """
    qute_configdata.init()
    return [setting for setting in qute_configdata.DATA]


def parse_config_line(line):
    """
    Get setting name from config-line.

    Args:
        line: The line from the config-file to be parsed (str)

    Return:
        Str if found, else None
    """
    match = re.search('^(#( )?)?c\.(?P<setting>.*) = .*', line)
    if match:
        return match.group('setting')


def parse_config_file(path):
    """
    Parse a single config-file.

    Args:
        path: A config-file path, as pathlib.Path

    Return:
        Dict {'setting': ['/path/to/file:line-number', ...], ...}
    """
    settings = {}
    with path.open(mode='r') as f:
        lines = [x.strip() for x in f.readlines()]

    for no, line in enumerate(lines):
        setting = parse_config_line(line)
        if setting:
            location = '{}:{}'.format(str(path), no + 1)
            if setting in settings:
                settings[setting].append(location)
            else:
                settings[setting] = [location]
    return settings


def get_local_settings(config_paths):
    """
    Parse all given config-files for settings.

    Args:
        config_paths: List of paths as pathlib.Path

    Return:
        Dict {'setting': ['/path/to/file:line-number', ...], ...}
    """
    settings = {}
    for path in config_paths:
        file_config = parse_config_file(path)
        for setting in file_config:
            if setting in settings:
                settings[setting] += file_config[setting]
            else:
                settings[setting] = file_config[setting]
    return settings


def compare_lists(list1, list2):
    """
    Compare two lists.

    Args:
        list1: Base list
        list2: List to be substracted

    Return:
        List of entries from list1 that are not in list2
    """
    return list(set(list1) - set(list2))


def print_it(data, naked):
    """
    If not args.naked, print a pretty table out of two lists.
    Else just print the list.

    Args:
        data: List of dicts [{'name': setting,
                              'location': location}, ...]
        naked: Bool: Whether to print location or not.
    """
    if naked:
        for setting in data:
            print(setting['name'])
    else:
        format_string = '{0:{length}}\033[1;30m{1}\033[1;m'
        # very hacky way to get the length of the largest name
        length = len(max([x['name'] for x in data], key=len)) + 1

        for setting in data:
            print(format_string.format(setting['name'],
                                       setting['location'],
                                       length=length))


def process_not_local(args, not_local):
    """
    Handle the output for settings not present in local config.

    Args:
        args: The arguments the script was invoked with
        not_local: List of strings --> settings not present in local config
    """
    if args.all:
        print('####################\n'
              'Not in local config:\n'
              '####################')

    if args.all or args.missing:
        url_format = 'qute://help/settings.html#{}'
        data = [{'name': setting,
                 'location': url_format.format(setting)}
                for setting in not_local]

        data_sorted = sorted(data, key=lambda k: k['location'])
        print_it(data_sorted, args.naked)


def process_not_qute(args, not_qute, local_settings):
    """
    Handle the output for settings not available in qutebrowser.

    Args:
        args: The arguments the script was invoked with
        not_qute: List of strings --> settings not available in qutebrowser
        local_settings: Dict {'setting': ['/path/to/file:line-number', ...],
                              ...}
    """

    def create_data_list_for_setting(cur_setting):
        """
        Create a list of dicts for a given setting.

        Args:
            cur_setting: Dict of current processed setting

        Return:
            A list of dicts [{'name': setting, 'location': location}, ...]
        """
        return [{'name': cur_setting, 'location': location}
                for location in local_settings[cur_setting]]

    if args.all:
        print('#############################\n'
              'Not available in qutebrowser:\n'
              '#############################')

    if args.all or args.dropped:
        data = []
        for setting in not_qute:
            data += create_data_list_for_setting(setting)

        data_sorted = sorted(data, key=lambda k: k['location'])
        print_it(data_sorted, args.naked)


def main():
    """
    qutebrowser-compare-config.py main function.
    """
    args = parse_arguments()
    qute_settings = get_available_settings()
    local_settings = get_local_settings(args.config_paths)

    not_local = compare_lists(qute_settings, local_settings.keys())
    not_qute = compare_lists(local_settings.keys(), qute_settings)

    if not_local:
        process_not_local(args,
                          not_local)

    if not_qute:
        # make some space if this is the second list
        if args.all and not_local:
            print()
        process_not_qute(args,
                         not_qute,
                         local_settings)


if __name__ == '__main__':
    main()
