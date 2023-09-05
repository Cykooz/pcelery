# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 19.03.2017
"""
from collections import deque
from typing import Optional

from billiard.einfo import ExceptionInfo
from celery.worker.request import Request
from kombu.transport.memory import Channel
from kombu.transport.virtual import Message
from pyramid.registry import Registry


class TasksQueue:

    def __init__(
            self,
            registry: Registry,
            queue_name='pcelery.default',
            clear=True,
            disabled_tasks: Optional[set[str]] = None,
    ):
        self.registry = registry
        self._queue_name = queue_name
        if queue_name in Channel.queues and clear:
            Channel.queues[queue_name].queue.clear()
        self.disabled_tasks = disabled_tasks or set()

    @property
    def _channel(self):
        with self.registry.celery.connection_or_acquire() as connection:
            if connection.transport.channels:
                return connection.transport.channels[0]

    @property
    def queue(self):
        if self._queue_name in Channel.queues:
            return Channel.queues[self._queue_name].queue
        return deque()

    @property
    def task_names(self):
        names = (m['headers']['task'] for m in self.queue)
        return (n for n in names if n not in self.disabled_tasks)

    def __len__(self):
        return len(list(self.task_names))

    def __getitem__(self, key) -> Message:
        if not self._channel:
            raise KeyError(key)
        queue = [m for m in self.queue if m['headers']['task'] not in self.disabled_tasks]
        return Message(queue[key], self._channel)

    def __contains__(self, item):
        return any(item == name for name in self.task_names)

    def _run(self, payload, ignore_errors=False):
        message = Message(payload, self._channel)
        req = Request(message, app=self.registry.celery)
        exc_info: ExceptionInfo = req.execute()
        if exc_info and not ignore_errors:
            exc_w_tb = exc_info.exception
            raise exc_w_tb.exc
        return exc_info

    def get_count_by_name(self, name):
        count = 0
        for t_name in self.task_names:
            if t_name == name:
                count += 1
        return count

    def run_oldest_task(self, name=None, ignore_errors=False):
        queue = self.queue
        if queue:
            if not name:
                while queue:
                    payload = queue.popleft()
                    if payload['headers']['task'] in self.disabled_tasks:
                        continue
                    return self._run(payload, ignore_errors)
            else:
                for i in range(len(queue)):
                    task_name = queue[i]['headers']['task']
                    if task_name in self.disabled_tasks:
                        continue
                    if task_name == name:
                        payload = queue[i]
                        del queue[i]
                        return self._run(payload, ignore_errors)

    def run_last_task(self, name=None, ignore_errors=False):
        queue = self.queue
        if not self.queue:
            return
        if not name:
            while queue:
                payload = self.queue.pop()
                if payload['headers']['task'] in self.disabled_tasks:
                    continue
                return self._run(payload, ignore_errors)
        else:
            count = len(queue)
            for i in range(count - 1, -1, -1):
                task_name = queue[i]['headers']['task']
                if task_name in self.disabled_tasks:
                    continue
                if task_name == name:
                    payload = queue[i]
                    del queue[i]
                    return self._run(payload, ignore_errors)

    def run_tasks_by_name(self, name, ignore_errors=False):
        count = self.get_count_by_name(name)
        while count:
            for _ in range(count):
                self.run_oldest_task(name, ignore_errors)
            count = self.get_count_by_name(name)

    def run_all_tasks(self, ignore_errors=False):
        count = len(self.queue)
        while count > 0:
            for _ in range(count):
                self.run_oldest_task(ignore_errors=ignore_errors)
            count = len(self.queue)

    def clear(self):
        self.queue.clear()

    def remove_oldest_task(self):
        queue = self.queue
        while queue:
            payload = self.queue.popleft()
            if payload['headers']['task'] not in self.disabled_tasks:
                return

    def remove_last_task(self):
        queue = self.queue
        while queue:
            payload = self.queue.pop()
            if payload['headers']['task'] not in self.disabled_tasks:
                return
