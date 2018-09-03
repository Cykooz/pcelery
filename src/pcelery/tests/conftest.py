# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 29.08.2017
"""
import pytest
from pyramid import testing
from pyramid.config import Configurator
from pyramid.interfaces import IRequestFactory, IRootFactory
from pyramid.request import Request, apply_request_extensions
from pyramid.scripting import prepare
from pyramid.threadlocal import RequestContext
from pyramid.traversal import DefaultRootFactory


def simple_app(global_config, **settings):
    """This function returns a Pyramid WSGI application."""
    config = Configurator(settings=settings)
    config.include('pcelery')
    config.set_celery_config({
        'testing': True,
    })
    return config.make_wsgi_app()


def create_app_env():
    settings = {
        'testing': True
    }
    wsgi_app = simple_app({}, **settings)
    env = prepare()
    env['app'] = wsgi_app
    return env


@pytest.fixture(name='app_config')
def app_config_fixture():
    settings = {}
    request = Request.blank('http://localhost')
    with testing.testConfig(request=request, settings=settings) as config:
        config.include('pcelery')
        config.set_celery_config({
            'testing': True,
        })
        config.scan()
        yield config


@pytest.fixture(name='pyramid_request')
def pyramid_request_fixture(app_config):
    """
    :rtype: pyramid.request.Request
    """
    registry = app_config.registry
    request_factory = registry.queryUtility(IRequestFactory, default=Request)
    request = request_factory.blank('http://localhost')
    request.registry = registry
    apply_request_extensions(request)
    # create pyramid root
    root_factory = request.registry.queryUtility(IRootFactory, default=DefaultRootFactory)
    root = root_factory(request)  # Initialise pyramid root
    if hasattr(root, 'set_request'):
        root.set_request(request)
    request.root = root
    context = RequestContext(request)
    context.begin()
    yield request
    request._process_finished_callbacks()
    context.end()
