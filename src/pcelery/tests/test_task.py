# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 29.08.2017
"""
import sys
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Optional

import pytest
from celery.exceptions import Retry
from pyramid.threadlocal import get_current_request

from .. import task
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
    assert std_out.getvalue().strip() == '5.4.0 (opalescent)'


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
