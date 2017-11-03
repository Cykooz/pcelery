# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 14.11.2016
"""
import six
from celery import Task as BaseTask
from celery.app import push_current_task, pop_current_task
from celery.signals import before_task_publish
from pyramid.request import Request, apply_request_extensions
from pyramid.threadlocal import manager, get_current_request
from pyramid.interfaces import IRootFactory, IRequestFactory
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
            # add self if this is a bound task
            if self.__self__ is not None:
                return self.run(self.__self__, *args, **kwargs)
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
        manager.push({
            'registry': self.pyramid_registry,
            'request': self.pyramid_request
        })
        try:
            return self._wrapped_run(*args, **kwargs)
        finally:
            if self.pyramid_request:
                self.pyramid_request._process_finished_callbacks()
            manager.pop()

    def _wrapped_run(self, *args, **kwargs):
        """This method may be overridden in child class"""
        # add self if this is a bound task
        if self.__self__ is not None:
            return self.run(self.__self__, *args, **kwargs)
        return self.run(*args, **kwargs)

    @property
    def pyramid_registry(self):
        """
        :rtype: pyramid.registry.Registry
        """
        app = self.app
        if app:
            return app.pyramid_registry

    @property
    def pyramid_request(self):
        """
        :rtype: pyramid.request.Request
        """
        request = getattr(self.request, 'pyramid_request', None)
        if not request:
            extra = getattr(self.request, EXTRA_PARAMS_NAME, {})
            data = extra.get('http_request', None)
            request = deserialize_request(data, self.pyramid_registry)
            self.request.pyramid_request = request
        if not hasattr(request, 'root'):
            # It is not real worker, most likely it is testing environment
            root_factory = self.pyramid_registry.queryUtility(IRootFactory, default=DefaultRootFactory)
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


def serialize_request(request):
    """
    :type request: pyramid.request.Request
    :rtype: dict
    """
    env = {key: value for key, value in request.environ.items()
           if key.isupper()}
    if 'CONTENT_LENGTH' in env:
        env['CONTENT_LENGTH'] = '0'
    data = {
        'REQUEST_ENV': env,
        'REQUEST_URL': request.url,
    }
    return data


def deserialize_request(data, registry, default_url='http://localhost'):
    """
    :type data: dict
    :type registry: pyramid.registry.Registry
    :type default_url: str
    :rtype: pyramid.request.Request
    """
    if data:
        url = data['REQUEST_URL']
        env = data['REQUEST_ENV']
        if six.PY2:
            url = _force_utf8(url)
            env = _force_dict_utf8(env)
    else:
        url = default_url
        env = None
    request_factory = registry.queryUtility(IRequestFactory, default=Request)
    request = request_factory.blank(url, env)
    request.registry = registry
    apply_request_extensions(request)
    return request


def _force_utf8(v):
    if isinstance(v, six.text_type):
        return v.encode('utf-8')
    return v


def _force_dict_utf8(d):
    values = []
    for k, v in six.iteritems(d):
        values.append((_force_utf8(k), _force_utf8(v)))
    return dict(values)
