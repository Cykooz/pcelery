"""Get Celery instance from Pyramid configuration."""

from copy import deepcopy

from celery import Celery, Task
from kombu import Exchange, Queue
from pyramid.registry import Registry

from .base_task import PyramidCeleryTask
from .interfaces import ICeleryQueuesFactory


def _get_celery_config(registry: Registry) -> dict:
    """Load Celery configuration from settings."""
    celery_config = registry.pop('pcelery_config', {})
    celery_config = deepcopy(celery_config)

    is_testing = celery_config.pop('testing', False)
    if is_testing:
        celery_config = {
            'app_name': celery_config.get('app_name'),
            'task_cls': celery_config.get('task_cls'),
            'beat_schedule': celery_config.get('beat_schedule'),
            'broker_url': 'memory://',
            'accept_content': ['json', 'msgpack', 'yaml'],
            'broker_heartbeat': 50,
            'result_backend': '',
            'task_serializer': 'json',
            'task_ignore_result': True,
            'task_acks_late': True,
            'worker_disable_rate_limits': True,
            'worker_prefetch_multiplier': 1,
            'worker_hijack_root_logger': False,
            'event_queue_ttl': 5,
            'event_queue_expires': 15,
            'enable_utc': True,
            'timezone': 'UTC',
            # Special for testing
            'worker_send_task_events': False,
            'worker_pool': 'solo',
            'worker_concurrency': 1,
            # Sets only one default queue that will receive all messages.
            'task_default_exchange': 'pcelery.default',
            'task_default_queue': 'pcelery.default',
            'task_default_routing_key': '',
            'task_queues': [
                Queue(
                    'pcelery.default',
                    Exchange('pcelery.default', type='topic'),
                    routing_key='*',
                ),
            ],
        }
    else:
        celery_queues = []
        # Add queues created by other applications
        for _, queues_factory in registry.getUtilitiesFor(ICeleryQueuesFactory):
            celery_queues += queues_factory(registry)

        task_queues = celery_config.setdefault('task_queues', [])
        task_queues.extend(celery_queues)

    return celery_config


def get_celery(registry) -> Celery:
    """Load and configure Celery app.

    Cache the loaded Celery app object on registry.

    :param registry: Use registry settings to load Celery
    """
    celery = getattr(registry, 'celery', None)
    if not celery:
        config = _get_celery_config(registry)
        app_name = config.pop('app_name', None) or 'pcelery'
        task_cls = config.pop('task_cls', None) or PyramidCeleryTask
        celery = registry.celery = Celery(
            app_name,
            task_cls=task_cls,
            loader='pcelery.loader:PyramidCeleryLoader',
        )
        celery.config_from_object(config)
        # Expose Pyramid registry to Celery app and tasks
        celery.pyramid_registry = registry

    return celery


class TaskProxy:
    """Late-bind Celery tasks to decorated functions.

    Normally ``celery.task()`` binds everything during import time.
    But we want to avoid this, as we don't want to deal with any configuration during import time.

    We wrap a decorated function with this proxy. Then we forward all
    the calls to Celery Task object after it has been bound during the end of configuration.
    """

    def __init__(self, original_func):
        name = original_func.__module__ + '.' + original_func.__name__
        self.original_func = original_func
        self.celery_task = None
        self.name = name

        # Venusian setup
        self.__venusian_callbacks__ = None
        self.__name__ = self.original_func.__name__

    def __str__(self):
        return f'TaskProxy for {self.original_func} bound to task {self.celery_task}'

    def __repr__(self):
        return self.__str__()

    def __call__(self, *args, **kwargs):
        if not self.celery_task:
            raise RuntimeError(
                'Celery task creation failed. Did config.scan() do '
                f'a sweep on {self.original_func}? TaskProxy tried '
                'to look up attribute: __call__'
            )
        return self.celery_task(*args, **kwargs)

    def bind_celery_task(self, celery_task):
        assert isinstance(celery_task, Task)
        self.celery_task = celery_task
        if 'name' in self.__dict__:
            del self.__dict__['name']

    def __getattr__(self, item):
        """Resolve all method calls to the underlying task."""

        if item == '__wrapped__':
            raise AttributeError(item)

        if not self.celery_task:
            raise RuntimeError(
                'Celery task creation failed. Did config.scan() do '
                f'a sweep on {self.name}? TaskProxy tried '
                f'to look up attribute: {item}'
            )

        return getattr(self.celery_task, item)
