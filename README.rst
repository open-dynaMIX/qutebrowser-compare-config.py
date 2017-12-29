qutebrowser-compare-config.py
=============================

Find settings for `qutebrowser <https://github.com/qutebrowser/qutebrowser>`__ that are not present in local config
and vice versa.

1. Get the list of configurable settings from qutebrowser.
2. Parse local qutebrowser config file(s) and gather all present settings.
3. Compare the two lists.

Takes a list of config-files and/or config-file-directories
and parses all \*.py-files.

It also takes commented out settings from the local config into account.

This will not try to resolve the found issues. Your config files will only be
read, never written to.


Usage and options
-----------------

::

    usage: qutebrowser-compare-config.py [-h] [-m] [-d] [-n] [config [config ...]]

    Find settings for qutebrowser that are not present in local config and vice versa.

    positional arguments:
      config         List of config files or directories. Defaults to standard
                     location of config.py

    optional arguments:
      -h, --help     show this help message and exit
      -m, --missing  only list settings missing in local config
      -d, --dropped  only list settings not present in qutebrowser
      -n, --naked    omit additional information (file/line-number/URL


Example screenshot
------------------

.. image:: ./screenshot.png


Limitations
-----------

1. This will not read values set in autoconf.yml.
2. There is no guarantee, that all of this works 100% (parsing the user-written config will always be rather hacky). But it should provide a good starting point for cleaning up.
3. Only tested on Linux, but it should also work on macOS/Windows.
