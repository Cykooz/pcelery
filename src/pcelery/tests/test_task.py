# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 29.08.2017
"""

import sys
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Optional, Type
from pyramid import testing

import pytest
from celery import Task
from celery.exceptions import Retry
from pyramid.request import Request
from pyramid.threadlocal import get_current_request

from .. import task, add_celery_tasks_alt_name_factory, get_celery
from ..commands import pcelery
from ..testing import TasksQueue


@task(bind=True, max_retries=100)
def first_task(self, request_id, retry=0, dont_retry_after: Optional[int] = None):
    request = self.pyramid_request
    if retry > 0:
        registry = request.registry
        if not hasattr(registry, 'first_task_runs'):
            registry.first_task_runs = 0
        if not dont_retry_after or dont_retry_after > registry.first_task_runs:
            registry.first_task_runs += 1
            raise self.retry(countdown=retry)
    if self.request.called_directly:
        assert id(request) == request_id
    else:
        assert id(request) != request_id


def test_celery(pyramid_request):
    cur_request_id = id(get_current_request())
    assert cur_request_id == id(pyramid_request)

    tasks_queue = TasksQueue(pyramid_request.registry)
    first_task.delay(cur_request_id)
    assert tasks_queue.get_count_by_name(first_task.name) == 1
    tasks_queue.run_all_tasks()

    first_task(cur_request_id)


@contextmanager
def stdout_to_stringio() -> StringIO:
    old_stdout = sys.stdout
    sys.stdout = local_stdout = StringIO()
    try:
        yield local_stdout
    finally:
        sys.stdout = old_stdout


def test_cli_command():
    ini_path = Path(__file__).parent / 'pyramid.ini'
    old_argv = sys.argv.copy()
    sys.argv.clear()
    args = ['--ini', str(ini_path), '--version']
    sys.argv.append('./bin/pcelery')
    sys.argv.extend(args)
    with pytest.raises(SystemExit) as exc_info:
        with stdout_to_stringio() as std_out:
            pcelery(args)

    sys.argv.clear()
    sys.argv.extend(old_argv)

    assert exc_info.value.args[0] == 0
    assert std_out.getvalue().strip() == '5.6.2 (recovery)'


def test_tasks_queue_retry(pyramid_request):
    cur_request_id = id(get_current_request())
    registry = pyramid_request.registry

    tasks_queue = TasksQueue(pyramid_request.registry)
    first_task.delay(cur_request_id, retry=1)
    assert tasks_queue.get_count_by_name(first_task.name) == 1
    with pytest.raises(Retry):
        tasks_queue.run_all_tasks()
    assert tasks_queue.get_count_by_name(first_task.name) == 1
    assert registry.first_task_runs == 1

    registry.first_task_runs = 0
    with pytest.raises(Retry):
        tasks_queue.run_all_tasks(max_retries=2)
    assert tasks_queue.get_count_by_name(first_task.name) == 1
    assert registry.first_task_runs == 3

    tasks_queue.clear()
    first_task.delay(cur_request_id, retry=1, dont_retry_after=3)
    assert tasks_queue.get_count_by_name(first_task.name) == 1
    tasks_queue.run_all_tasks(max_retries=100)
    assert tasks_queue.get_count_by_name(first_task.name) == 0
    assert registry.first_task_runs == 3


@task(bind=True)
def order_task_1(self):
    request = self.pyramid_request
    request.registry.tasks_order.append(1)


@task(bind=True)
def order_task_2(self):
    request = self.pyramid_request
    request.registry.tasks_order.append(2)


@task(bind=True)
def order_task_master(self):
    request = self.pyramid_request
    request.registry.tasks_order.append(0)
    order_task_1.delay()
    order_task_2.delay()


def test_tasks_order(pyramid_request):
    registry = pyramid_request.registry
    registry.tasks_order = []
    tasks_queue = TasksQueue(registry)
    order_task_1.delay()
    order_task_2.delay()
    tasks_queue.run_all_tasks()
    assert registry.tasks_order == [1, 2]

    registry.tasks_order.clear()
    order_task_master.delay()
    tasks_queue.run_all_tasks()
    assert registry.tasks_order == [0, 1, 2]


def alt_task_name(task_class: Type[Task]) -> Optional[str]:
    if task_class.name.endswith('.first_task'):
        return 'renamed.first_task'
    return None


def test_alt_task_name():
    settings = {}
    request = Request.blank('http://localhost')
    with testing.testConfig(request=request, settings=settings) as config:
        config.include('pcelery')
        config.set_celery_config({'testing': True})
        add_celery_tasks_alt_name_factory(config, alt_task_name)
        config.scan()
        celery = get_celery(config.registry)
        assert celery.tasks['renamed.first_task'].name == first_task.name
