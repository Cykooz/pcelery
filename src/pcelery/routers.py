# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 03.08.2018
"""


class RouterByRoutingKey(object):
    """Routes tasks by it routing_key only.

    Usage:

        .. code-block:: python

            def includeme(config):
                config.include('pcelery')

                from kombu.entity import Exchange, Queue

                default_exchange = Exchange('backend.default', type='direct')
                celery_config = {
                    ...
                    'task_default_exchange': 'backend.default',
                    'task_default_routing_key': 'middle_priority',
                    'task_default_queue': 'backend.middle',
                    'task_queues': [
                        Queue('backend.high', default_exchange, routing_key='high_priority'),
                        Queue('backend.middle', default_exchange, routing_key='middle_priority'),
                        Queue('backend.low', default_exchange, routing_key='low_priority'),
                    ],
                    'task_routes': [
                        RouterByRoutingKey(default_queue_name='backend.middle'),
                    ],
                }

                config.set_celery_config(celery_config)
                config.scan()
    """

    def __init__(self, default_queue_name):
        self.default_queue_name = default_queue_name

    def __call__(self, name, args, kwargs, options, task=None, **kw):
        routing_key = options.get('routing_key', None)
        if task and routing_key:
            # Find queue by it routing_key
            celery_conf = task.app.conf
            exchange_name = options.get('exchange') or celery_conf['task_default_exchange']
            for queue in celery_conf['task_queues']:
                if queue.exchange.name == exchange_name and queue.routing_key == routing_key:
                    return queue.name
            return celery_conf['task_default_queue'] or self.default_queue_name
        return self.default_queue_name
