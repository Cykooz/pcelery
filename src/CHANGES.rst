..  Changelog format guide.
    - Before make new release of core egg you MUST add here a header for new version with name "Next release".
    - After all headers and paragraphs you MUST add only ONE empty line.
    - At the end of sentence which describes some changes SHOULD be identifier of task from our task manager.
      This identifier MUST be placed in brackets. If a hot fix has not the task identifier then you
      can use the word "HOTFIX" instead of it.
    - At the end of sentence MUST stand a point.
    - List of changes in the one version MUST be grouped in the next sections:
        - Features
        - Changes
        - Bug Fixes
        - Docs

CHANGELOG
*********

Next release
============

Bug Fixes
---------

- Fixed task registration for Pyramid >= 2.0.

0.4 (2021-04-27)
================

Features
--------

- Added support of ``celery>=5.0``.

Backward incompatible changes
-----------------------------

- Dropped support of ``celery<5.0``.
- Dropped support of ``Python<3.6``.

0.3 (2018-09-03)
================

Features
--------

- Added support of ``celery>=4.2``.

Backward incompatible changes
-----------------------------

- Dropped support of ``celery<4.2``.

0.2 (2018-08-03)
================

Features
--------

- Added tasks router by value of task ``routing_key`` only.

Docs
----

- Added documentation section with description of ``Celery`` configuration.

0.1.2 (2017-12-19)
==================

Bug Fixes
---------

- Fixed task decorator for correct creation of new celery queues using
  ``add_celery_queues_factory`` directive.

0.1 (2017-12-04)
================

Features
--------

- Initial release.
