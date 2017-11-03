pcelery
*******

This module implements integration of ``Celery`` with ``Pyramid`` framework.

Task
====

For define task you MUST use decorator ``pcelery.task``. This
decorator works like the ``app.task`` decorator from ``Celery``. But it is not
create and register task in import time. You MUST use ``config.scan()`` to pick
up and register tasks in the current celery application.

Example:

*package/__init__.py*

    .. code-block:: python

        def includeme(config):
            config.include('pcelery')

            config.scan()


*package/tasks.py*

    .. code-block:: python

        from pcelery import task


        @task(bind=True, ignore_result=True, routing_key='high_priority')
        def do_my_work(self, arg1, kwarg2=None):
            pass

Inside of task you could retrieve pyramid request and registry through task instance:

    .. code-block:: python

        from pcelery import task


        @task(bind=True)
        def do_my_work(self, arg1, kwarg2=None):
            request = self.pyramid_request
            with request.tm:
               utility = self.pyramid_registry.getUtility(IMyUtility)
               utility.save_result(request.db_session)
            # Or you could retrieve registry directly from request
            # request.registry.getUtility(IMyUtility)

Queues
======

This module provides special directive for pyramid configurator -
``add_celery_queues_factory``. With helps of this directive you may
add custom queues to ``Celery`` settings.

Examples:

    .. code-block:: python

        from kombu import Exchange, Queue


        default_exchange = Exchange('default', type='direct')


        def includeme(config):
            config.include('pcelery')

            config.add_celery_queues_factory(create_my_app_queues)
            config.add_celery_queues_factory(create_custom_queues, name='my_custom_queues')
            config.scan(ignore=scan_ignore())


        def create_my_app_queues(registry):
            exchange = Exchange('my_app', type='direct')
            queue = Queue('my_app.high', exchange, routing_key='high_priority')
            return [queue]


        def create_custom_queues(registry):
            return [
                Queue('default.contacts', default_exchange, routing_key='contacts'),
                Queue('default.photos', default_exchange, routing_key='photos'),
            ]
