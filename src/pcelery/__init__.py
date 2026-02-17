# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 03.08.2017
"""

import re
from copy import deepcopy
from typing import Callable, Optional, Type

import venusian
from celery import Task
from pyramid.config import Configurator
from pyramid.registry import Registry

from .interfaces import ICeleryQueuesFactory
from .utils import TaskProxy, get_celery


def includeme(config: Configurator):
    config.add_directive('add_celery_queues_factory', add_celery_queues_factory)
    config.add_directive('set_celery_config', set_celery_config)
    ignore = [
        re.compile('tests$').search,
        re.compile('testing$').search,
        re.compile('docs$').search,
        re.compile('conftest$').search,
    ]
    config.scan(ignore=ignore)


def add_celery_queues_factory(
    config: Configurator,
    factory: Callable[[Registry], list],
    name: Optional[str] = None,
):
    """This function registers a utility that creates celery queues."""
    name = name or factory.__name__
    config.registry.registerUtility(factory, ICeleryQueuesFactory, name=name)


def set_celery_config(config: Configurator, celery_config: dict):
    """This function storing a celery configuration in the pyramid registry."""
    config.registry['pcelery_config'] = deepcopy(celery_config)


def add_celery_tasks_alt_name_factory(
    config: Configurator,
    name_factory: Callable[[Type[Task]], Optional[str]],
):
    """This function storing a celery configuration in the pyramid registry."""
    factories = config.registry.setdefault('pcelery_alt_name_factories', [])
    factories.append(name_factory)


def task(**kwargs):
    """Configuration compatible task decorator.

    Tasks are picked up by :py:meth:`pyramid.config.Configurator.scan`
    run on the module, not during import time.
    Otherwise we mimic the behavior of :py:meth:`celery.Celery.task`.

    :param kwargs: Passed to Celery task decorator
    """

    def _inner(func):
        proxy = TaskProxy(func)

        def callback(scanner, name, task_proxy):
            config = scanner.config

            def register():
                registry = config.registry
                celery = get_celery(registry)
                celery_task = celery.task(task_proxy.original_func, **kwargs)
                if alt_name_factories := config.registry.get(
                    'pcelery_alt_name_factories', None
                ):
                    for alt_name_factory in alt_name_factories:
                        if alt_name := alt_name_factory(celery_task):
                            celery.tasks[alt_name] = celery_task
                proxy.bind_celery_task(celery_task)

            config.action('bind_celery_task - %s' % name, register)

        venusian.attach(proxy, callback, category='pyramid')
        return proxy

    return _inner
