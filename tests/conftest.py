#!/usr/bin/python3
#
# shared pytest fixtures for linuxmuster-base7
# thomas@linuxmuster.net
# 20260809
#
"""
Shared pytest configuration.

Several modules under src/linuxmuster_base7 do
`sys.path.insert(0, '/usr/lib/linuxmuster'); import environment` to reach
the `environment` module shipped by the linuxmuster-common package
(Pre-Depends of this package, see debian/control). On an installed system,
or a build/test container that installs Depends, that path exists. On a
bare source checkout it doesn't.

This resolves it from either location, so tests can run without requiring
linuxmuster-common to be installed system-wide:
1. /usr/lib/linuxmuster/environment.py (installed system / build container)
2. ../linuxmuster-common/lib/environment.py (local multi-repo dev checkout,
   linuxmuster-common as a sibling of this repo)

If neither is found, `environment` stays unimportable and tests that need
it are expected to `pytest.importorskip('environment')` themselves rather
than fail with a confusing ModuleNotFoundError.
"""

import sys
from pathlib import Path


def _find_environment_dir():
    installed = Path('/usr/lib/linuxmuster/environment.py')
    if installed.is_file():
        return str(installed.parent)
    sibling = (Path(__file__).resolve().parent.parent.parent
               / 'linuxmuster-common' / 'lib' / 'environment.py')
    if sibling.is_file():
        return str(sibling.parent)
    return None


_env_dir = _find_environment_dir()
if _env_dir:
    sys.path.insert(0, _env_dir)
