"""
:Authors: cykooz
:Date: 22.09.2015
"""


def runtests():
    import sys
    from os import environ
    from pathlib import Path

    import pytest

    root_dir_path = Path(__file__).parent / '..' / '..'
    cfg_path = root_dir_path / 'src' / 'pyproject.toml'

    args = sys.argv[1:]
    args = [
        '-c',
        str(cfg_path),
        '--rootdir',
        str(root_dir_path),
    ] + args
    environ['IS_TESTING'] = 'true'

    return pytest.main(args)
