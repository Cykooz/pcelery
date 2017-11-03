# -*- coding: utf-8 -*-
"""
:Authors: cykooz
:Date: 19.05.2017
"""
from zope.interface.interface import Interface


class ICeleryQueuesFactory(Interface):

    def __call__(registry):
        """Returns list of celery queues."""
