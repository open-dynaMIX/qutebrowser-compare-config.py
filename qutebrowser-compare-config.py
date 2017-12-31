#!/usr/bin/env python3

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
and vice versa. Also check if default values are up-to-date.

1. Get the list of configurable settings from qutebrowser.
2. Parse local qutebrowser config file(s) and gather all present settings.
3. Compare the two lists.
4. Treat commented out settings as defaults and check if they're up-to-date.

Takes a list of config-files and/or config-file-directories
and parses all *.py-files.

It also takes commented out settings from the local config into account.

This will not try to resolve the found issues. Your config files will only be
read, never written to.

@newfield epilog: Epilog
"""


import argparse
import re
from pathlib import Path
from qutebrowser.config import configdata as qute_configdata
from qutebrowser.utils import standarddir as qute_standarddir


__title__ = 'qutebrowser-compare-config.py'
__description__ = ('Find settings for qutebrowser that are not present in '
                   'local config and vice versa. Also check if default values '
                   'are up-to-date.')
__epilog__ = 'Omitting -m, -d and -c is the same as -mdc.'
__copyright__ = 'Copyright 2017, Fabio Rämi'
__license__ = 'GPL'
__author__ = 'Fabio Rämi'


def parse_arguments():
    """
    Parse all arguments.
    """
    def check_what_to_do():
        """
        Check what to do and set args.print_headers.
        """
        count = 0
        args.print_headers = True
        for i in [args.missing, args.dropped, args.defaults]:
            if i:
                count += 1
        if count == 1:
            args.print_headers = False
        elif count == 0:
            args.missing = True
            args.dropped = True
            args.defaults = True

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
                                     epilog=__epilog__,
                                     formatter_class=argparse.
                                     RawDescriptionHelpFormatter)

    parser.add_argument('config', type=str, nargs='*',
                        default=[],
                        help='List of config files or directories. '
                        'Defaults to standard location of config.py')

    parser.add_argument('-m', '--missing', dest='missing',
                        action='store_true',
                        help='list settings missing in local config')

    parser.add_argument('-d', '--dropped', dest='dropped',
                        action='store_true',
                        help='list settings not present in '
                        'qutebrowser')

    parser.add_argument('-c', '--changed-defaults', dest='defaults',
                        action='store_true',
                        help='treat commented out settings as defaults and '
                        'compare values with default values from qutebrowser')

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
        Dict {setting: default value, ...}
    """
    qute_configdata.init()
    return {setting: qute_configdata.DATA[setting].default
            for setting in qute_configdata.DATA}


def parse_config_line(line):
    """
    Get setting name from config-line.

    Args:
        line: The line from the config-file to be parsed (str)

    Return:
        Tuple: (Str, Str, Bool) if found, else (None, None, None)
    """
    match = re.search('^(#( )?)?c\.(?P<setting>.*) = (?P<value>.*)', line)
    if match:
        if re.search('^#( )?', line):
            defined = False
        else:
            defined = True

        return match.group('setting'), match.group('value'), defined
    else:
        return None, None, None


def parse_config_file(path):
    """
    Parse a single config-file.

    Args:
        path: A config-file path, as pathlib.Path

    Return:
        Dict {'setting': [{'location': /path/to/file:line-number',
                           'value': str,
                           'defined': bool}, ...], ...}
    """
    settings = {}
    with path.open(mode='r') as f:
        lines = [x.strip() for x in f.readlines()]

    for no, line in enumerate(lines):
        setting, value, is_set = parse_config_line(line)
        if setting:
            location = '{}:{}'.format(str(path), no + 1)
            if setting in settings:
                settings[setting].append({'location': location,
                                          'value': value,
                                          'defined': is_set})
            else:
                settings[setting] = [{'location': location,
                                      'value': value,
                                      'defined': is_set}]
    return settings


def get_local_settings(config_paths):
    """
    Parse all given config-files for settings.

    Args:
        config_paths: List of paths as pathlib.Path

    Return:
        Dict {'setting': [{'location': /path/to/file:line-number',
                           'value': str,
                           'defined': bool}, ...], ...}
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


def compare_dict_keys(dict1, dict2):
    """
    Compare keys od two dicts.

    Args:
        dict1: Base dict
        dict2: Dict to be substracted

    Return:
        List of keys from dict1 that are not in dict2
    """
    return list(set(dict1.keys()) - set(dict2.keys()))


def render_it(data, naked):
    """
    If not args.naked, render a pretty table out of two lists.
    Else just render the list of settings.

    Args:
        data: List of dicts [{'name': setting,
                              'location': location,
                              'additional_lines': [str, ...]}, ...]
        naked: Bool: Whether to print location or not.

    Return:
        List of strings
    """
    result = []
    if naked:
        # prevent duplicates
        data_list = [setting for setting in data]
        for setting in data_list:
            result.append(setting['name'])
    else:
        format_string = '{0:{length}}\033[1;30m{1}\033[1;m'
        # very hacky way to get the length of the largest name
        length = len(max([x['name'] for x in data], key=len)) + 1

        for setting in data:
            result.append(format_string.format(setting['name'],
                                               setting['location'],
                                               length=length))
            if not naked:
                if 'additional_lines' in setting:
                    for line in setting['additional_lines']:
                        result.append(line)

    return result


def process_not_local(args, not_local):
    """
    Handle the output for settings not present in local config.

    Args:
        args: The arguments the script was invoked with
        not_local: List of strings --> settings not present in local config

    Return:
        List of strings
    """
    data = [{'name': setting,
             'location': 'qute://help/settings.html#{}'.format(setting)}
            for setting in not_local]

    data_sorted = sorted(data, key=lambda k: k['location'])
    if data_sorted:
        return render_it(data_sorted, args.naked)


def process_not_qute(args, not_qute, local_settings):
    """
    Handle the output for settings not available in qutebrowser.

    Args:
        args: The arguments the script was invoked with
        not_qute: List of strings --> settings not available in qutebrowser
        local_settings: Dict {'setting': ['/path/to/file:line-number', ...],
                              ...}

    Return:
        List of strings
    """
    def create_data_list_for_setting(cur_setting):
        """
        Create a list of dicts for a given setting.

        Args:
            cur_setting: Dict of current processed setting

        Return:
            A list of dicts [{'name': setting, 'location': location}, ...]
        """
        return [{'name': cur_setting, 'location': location['location']}
                for location in local_settings[cur_setting]]

    data = []
    for setting in not_qute:
        data += create_data_list_for_setting(setting)

    data_sorted = sorted(data, key=lambda k: k['location'])
    if data_sorted:
        return render_it(data_sorted, args.naked)


def process_defaults(args, qute_settings, not_qute, local_settings):
    """
    Handle the output for changed default values in qutebrowser.

    Args:
        args: The arguments the script was invoked with
        qute_settings: Dict of settings {setting: default value, ...}
        not_qute: List of strings --> settings not available in qutebrowser
        local_settings: Dict {'setting': ['/path/to/file:line-number', ...],
                              ...}

    Return:
        List of strings
    """
    changes = []
    for setting, locations in local_settings.items():
        if setting in not_qute:
            continue
        for location in locations:
            if location['defined']:
                continue
            if not eval(location['value']) == qute_settings[setting]:
                default = '    {}'.format(qute_settings[setting])
                url = ('    \033[1;30mqute://help/settings.html#{}'
                       '\033[1;m'.format(setting))
                additional_lines = [default, url]

                changes.append({'name': setting,
                                'location': location['location'],
                                'additional_lines': additional_lines})

    changes_sorted = sorted(changes, key=lambda k: k['location'])
    if changes_sorted:
        return render_it(changes_sorted, args.naked)


def print_it(result, print_headers):
    """
    Print the lists.

    Args:
        result: List of strings
        print_headers: Whether to print the headers (bool)
    """
    for count, result_list in enumerate(result):
        if print_headers:
            # make some space if this is not the first list
            if count > 0:
                print()
            print(result_list['header'])
        for entry in result_list['list']:
            print(entry)


def main():
    """
    qutebrowser-compare-config.py main function.
    """
    args = parse_arguments()
    qute_settings = get_available_settings()
    local_settings = get_local_settings(args.config_paths)

    not_local = compare_dict_keys(qute_settings, local_settings)
    not_qute = compare_dict_keys(local_settings, qute_settings)

    results = []

    if args.missing:
        missing_header = ('####################\n'
                          'Not in local config:\n'
                          '####################')
        missing_rendered = process_not_local(args,
                                             not_local)
        if missing_rendered:
            results.append({'header': missing_header,
                            'list': missing_rendered})

    if args.dropped:
        dropped_header = ('#############################\n'
                          'Not available in qutebrowser:\n'
                          '#############################')
        dropped_rendered = process_not_qute(args,
                                            not_qute,
                                            local_settings)
        if dropped_rendered:
            results.append({'header': dropped_header,
                            'list': dropped_rendered})

    if args.defaults:
        defaults_header = ('#######################\n'
                           'Changed default values:\n'
                           '#######################')
        defaults_rendered = process_defaults(args,
                                             qute_settings,
                                             not_qute,
                                             local_settings)
        if defaults_rendered:
            results.append({'header': defaults_header,
                            'list': defaults_rendered})

    print_it(results, args.print_headers)


if __name__ == '__main__':
    main()
