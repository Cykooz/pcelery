# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 14.11.2016
"""
from typing import Optional

from celery import Task as BaseTask
from celery.app import pop_current_task, push_current_task
from celery.signals import before_task_publish
from pyramid.interfaces import IRequestFactory, IRootFactory
from pyramid.registry import Registry
from pyramid.request import Request, apply_request_extensions
from pyramid.threadlocal import RequestContext, get_current_request
from pyramid.traversal import DefaultRootFactory


EXTRA_PARAMS_NAME = 'pcelery.extra'


class PyramidCeleryTask(BaseTask):

    def _call_directly(self, *args, **kwargs):
        # Emulate BaseTask.__call__()
        push_current_task(self)
        self.push_request(args=args, kwargs=kwargs)
        try:
            request = get_current_request()  # TODO: fix it - replace to explicitly passed keyword argument
            self.request.pyramid_request = request
            return self.run(*args, **kwargs)
        finally:
            del self.request.pyramid_request
            self.pop_request()
            pop_current_task()

    def __call__(self, *args, **kwargs):
        if self.request.called_directly:
            return self._call_directly(*args, **kwargs)

        # This method in BaseTask called only if a task called directly.
        # Celery do not run this method if it is not customized in the sub-class.
        # So we not need to emulate base version of this method if it is not called directly.
        context = RequestContext(self.pyramid_request)
        context.begin()
        try:
            return self._wrapped_run(*args, **kwargs)
        finally:
            context.request._process_finished_callbacks()
            context.end()

    def _wrapped_run(self, *args, **kwargs):
        """This method may be overridden in child class"""
        return self.run(*args, **kwargs)

    @property
    def pyramid_registry(self) -> Optional[Registry]:
        app = self.app
        if app:
            return app.pyramid_registry

    @property
    def pyramid_request(self) -> Request:
        request = getattr(self.request, 'pyramid_request', None)
        if not request:
            extra = getattr(self.request, EXTRA_PARAMS_NAME, {})
            data = extra.get('http_request', None)
            request = deserialize_request(data, self.pyramid_registry)
            self.request.pyramid_request = request
        if not hasattr(request, 'root'):
            # It is not real worker, most likely it is testing environment
            root_factory = self.pyramid_registry.queryUtility(
                IRootFactory,
                default=DefaultRootFactory
            )
            request.root = root_factory(request)
        return request


@before_task_publish.connect
def add_params_to_task(sender=None, body=None, **kwargs):
    if isinstance(body, tuple):
        embed = body[2]  # http://docs.celeryproject.org/en/latest/internals/protocol.html#definition
        request = get_current_request()
        extra = {
            'http_request': serialize_request(request),
        }
        embed[EXTRA_PARAMS_NAME] = extra


def serialize_request(request: Request) -> dict:
    env = {
        key: value
        for key, value in request.environ.items()
        if key.isupper()
    }
    if 'CONTENT_LENGTH' in env:
        env['CONTENT_LENGTH'] = '0'
    data = {
        'REQUEST_ENV': env,
        'REQUEST_URL': request.url,
    }
    return data


def deserialize_request(
        data: dict,
        registry: Registry,
        default_url='http://localhost'
) -> Request:
    if data:
        url = data['REQUEST_URL']
        env = data['REQUEST_ENV']
    else:
        url = default_url
        env = None
    request_factory = registry.queryUtility(IRequestFactory, default=Request)
    request = request_factory.blank(url, env)
    request.registry = registry
    apply_request_extensions(request)
    return request
