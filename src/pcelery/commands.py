# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 25.01.2017
"""

import argparse
import os
import sys
from argparse import ArgumentParser
from typing import List

from celery.bin.celery import celery as celery_main
from pyramid.paster import bootstrap
from pyramid.util import DottedNameResolver

from .utils import get_celery


def pcelery(args=None):
    argv = list(sys.argv)
    if args is None:
        args = argv[1:]

    parser = argparse.ArgumentParser(description='Execute celery command')
    parser.add_argument(
        '--ini',
        required=True,
        help='The URI to the pyramid configuration file.',
    )
    parser.add_argument(
        '--setup',
        dest='setup',
        help='A callable that will be passed the environment '
        'before it is made available to the celery.',
    )
    parsed_args, unknown_args = parser.parse_known_args(args)
    config_uri = parsed_args.ini
    with bootstrap(config_uri) as env:
        if parsed_args.setup:
            # call the setup callable
            resolver = DottedNameResolver(None)
            setup = resolver.maybe_resolve(parsed_args.setup)
            setup(env)
        return run_celery(env['request'], args=unknown_args)


def run_celery(request, args: List[str], add_ini_option=True):
    app = getattr(request.registry, 'celery', None)
    if not app:
        app = get_celery(request.registry)
    os.environ['CELERY_LOADER'] = 'pcelery.loader.PyramidCeleryLoader'
    app.set_default()
    if add_ini_option:
        app.user_options['preload'].add(add_preload_arguments)
    return celery_main(args, auto_envvar_prefix='CELERY')


def add_preload_arguments(parser: ArgumentParser):
    parser.add_argument(
        '--ini',
        help='The URI to the pyramid configuration file.',
    )
