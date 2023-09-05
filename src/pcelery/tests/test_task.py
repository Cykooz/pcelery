# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 29.08.2017
"""
import sys
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

import pytest
from pyramid.threadlocal import get_current_request

from .. import task
from ..commands import pcelery
from ..testing import TasksQueue


@task(bind=True)
def first_task(self, request_id):
    request = self.pyramid_request
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
    assert std_out.getvalue().strip() == '5.3.4 (emerald-rush)'
