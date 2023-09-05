from celery.loaders.base import BaseLoader


class PyramidCeleryLoader(BaseLoader):
    """Celery command line loader for Pyramid."""

    def read_configuration(self, env='CELERY_CONFIG_MODULE'):
        raise RuntimeError(
            'Run Celery by special command (typically it is pcelery).'
        )

    def import_task_module(self, module):
        raise RuntimeError(
            'Imports Celery config directive is not '
            'supported. Use config.scan() to pick up tasks.'
        )
