"""AuthLab: a sign-up / log-in app built around search and sort algorithms written from scratch."""

import sys

# Checked here, the first module Python loads, so older versions get a clear
# message instead of a confusing error somewhere else.
if sys.version_info < (3, 10):
    sys.exit("This app needs Python 3.10 or newer (you have %d.%d)." % sys.version_info[:2])

__version__ = "2.0.0"
