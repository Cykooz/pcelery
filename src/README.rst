pcelery
*******

This module implements integration of ``Celery`` with ``Pyramid`` framework.

Configuration
=============

To configure ``Celery`` application you MUST use method ``set_celery_config()``
of ``Pyramid Configurator``.

*backend/celery/__init__.py*

    .. code-block:: python

        def includeme(config):
            config.include('pcelery')

            from kombu.entity import Exchange, Queue

            default_exchange = Exchange('backend.default', type='direct')
            celery_config = {
                'app_name': 'backend',
                'broker_url': 'amqp://user:pswd@localhost:5672/backend',
                'accept_content': ['json', 'msgpack', 'yaml'],
                'result_backend': '',
                'task_serializer': 'json',
                'task_ignore_result': True,
                'task_acks_late': True,
                'task_default_exchange': 'backend.default',
                'task_default_routing_key': 'middle_priority',
                'task_default_queue': 'backend.middle',
                'task_queues': [
                    Queue('backend.high', default_exchange, routing_key='high_priority'),
                    Queue('backend.middle', default_exchange, routing_key='middle_priority'),
                    Queue('backend.low', default_exchange, routing_key='low_priority'),
                ]
            }
            config.set_celery_config(celery_config)
            config.scan()

Task
====

For define task you MUST use decorator ``pcelery.task``. This
decorator works like the ``app.task`` decorator from ``Celery``. But it is not
create and register task in import time. You MUST use ``config.scan()`` to pick
up and register tasks in the current celery application.

Example:

*backend/users/__init__.py*

    .. code-block:: python

        def includeme(config):
            config.include('backend.celery')

            config.scan()


*backend/users/tasks.py*

    .. code-block:: python

        from pcelery import task


        @task(bind=True, ignore_result=True, routing_key='high_priority')
        def update_user_status(self, arg1, kwarg2=None):
            pass

Inside of task you could retrieve pyramid request and registry through task instance:

*backend/users/tasks.py*

    .. code-block:: python

        from pcelery import task


        @task(bind=True)
        def update_user_status(self, arg1, kwarg2=None):
            request = self.pyramid_request
            with request.tm:
               utility = self.pyramid_registry.getUtility(IMyUtility)
               utility.save_result(request.db_session)
            # Or you could retrieve registry directly from request:
            # utility = request.registry.getUtility(IMyUtility)

Queues
======

This package provides special directive for ``Pyramid Configurator`` -
``add_celery_queues_factory``. With helps of this directive you may register
custom queues not only from application that setup ``Celery`` configuration.

*backend/users/__init__.py*

    .. code-block:: python

        from kombu import Exchange, Queue


        def includeme(config):
            config.include('backend.celery')

            config.add_celery_queues_factory(create_users_queues)
            config.scan(ignore=scan_ignore())


        def create_users_queues(registry):
            exchange = Exchange('users_exchange', type='direct')
            return [
                Queue('users.high', exchange, routing_key='high_priority'),
                Queue('users.low', exchange, routing_key='low_priority'),
            ]

