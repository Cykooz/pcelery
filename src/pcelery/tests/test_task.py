# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 29.08.2017
"""
import pytest
from pyramid.threadlocal import get_current_request

from .. import task
from ..testing import TasksQueue


@task(bind=True)
def first_task(self, request_id):
    request = self.pyramid_request
    if self.request.called_directly:
        assert id(request) == request_id
    else:
        assert id(request) != request_id


@pytest.mark.now
def test_celery(pyramid_request):
    cur_request_id = id(get_current_request())
    assert cur_request_id == id(pyramid_request)

    tasks_queue = TasksQueue(pyramid_request.registry)
    first_task.delay(cur_request_id)
    assert tasks_queue.get_count_by_name(first_task.name) == 1
    tasks_queue.run_all_tasks()

    first_task(cur_request_id)
