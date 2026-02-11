# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 03.08.2017
"""

import re
from copy import deepcopy

import venusian

from .interfaces import ICeleryQueuesFactory
from .utils import TaskProxy, get_celery


def includeme(config):
    config.add_directive('add_celery_queues_factory', add_celery_queues_factory)
    config.add_directive('set_celery_config', set_celery_config)
    ignore = [
        re.compile('tests$').search,
        re.compile('testing$').search,
        re.compile('docs$').search,
        re.compile('conftest$').search,
    ]
    config.scan(ignore=ignore)


def add_celery_queues_factory(config, factory, name=None):
    """This function registers a utility that creates celery queues.
    :type config: pyramid.config.Configurator
    :type factory: object
    :type name: string
    """
    name = name or factory.__name__
    config.registry.registerUtility(factory, ICeleryQueuesFactory, name=name)


def set_celery_config(config, celery_config):
    """This function storing a celery configuration in the pyramid registry.
    :type config: pyramid.config.Configurator
    :type celery_config: dict
    """
    config.registry['pcelery_config'] = deepcopy(celery_config)


def task(*args, **kwargs):
    """Configuration compatible task decorator.

    Tasks are picked up by :py:meth:`pyramid.config.Configurator.scan`
    run on the module, not during import time.
    Otherwise we mimic the behavior of :py:meth:`celery.Celery.task`.

    :param args: Passed to Celery task decorator
    :param kwargs: Passed to Celery task decorator
    """

    def _inner(func):
        proxy = TaskProxy(func)

        def callback(scanner, name, task_proxy):
            config = scanner.config

            def register():
                registry = config.registry
                celery = get_celery(registry)
                celery_task = celery.task(task_proxy.original_func, *args, **kwargs)
                proxy.bind_celery_task(celery_task)

            config.action('bind_celery_task - %s' % name, register)

        venusian.attach(proxy, callback, category='pyramid')
        return proxy

    return _inner
