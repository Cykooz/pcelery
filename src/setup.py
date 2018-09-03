# encoding: utf-8
import os
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
sys.path.append(HERE)

from setuptools import setup, find_packages, findall
import version


def find_package_data():
    ignore_ext = {'.py', '.pyc', '.pyo'}
    base_package = 'pcelery'
    package_data = {}
    root = os.path.join(HERE, base_package)
    for path in findall(root):
        if path.endswith('~'):
            continue
        ext = os.path.splitext(path)[1]
        if ext in ignore_ext:
            continue

        # Find package name
        package_path = os.path.dirname(path)
        while package_path != root:
            if os.path.isfile(os.path.join(package_path, '__init__.py')):
                break
            package_path = os.path.dirname(package_path)
        package_name = package_path[len(HERE) + 1:].replace(os.path.sep, '.')

        globs = package_data.setdefault(package_name, set())
        data_path = path[len(package_path) + 1:]
        data_glob = os.path.join(os.path.dirname(data_path), '*' + ext)
        globs.add(data_glob)
    for key, value in package_data.items():
        package_data[key] = list(value)
    return package_data


README = open(os.path.join(HERE, 'README.rst')).read()
CHANGES = open(os.path.join(HERE, 'CHANGES.rst')).read()

setup(
    name='pcelery',
    version=version.get_version(),
    description='Celery integration with Pyramid',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Framework :: Pyramid',
        'Topic :: Software Development :: Object Brokering',
        'Topic :: System :: Distributed Computing',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='',
    author='Kirill Kuzminykh',
    author_email='cykooz@gmail.com',
    url='https://github.com/Cykooz/pcelery',
    package_dir={'': '.'},
    packages=find_packages(),
    package_data=find_package_data(),
    zip_safe=False,
    extras_require={
        'test': [
            'pytest',
        ],
    },
    install_requires=[
        'setuptools',
        'celery>=4.2.0',
        'pyramid>=1.8.3',
        'venusian',
        'six',
    ],
    entry_points={
        'console_scripts':
            [
                'pcelery = pcelery.commands:pcelery',
                'pcelery_test = pcelery.runtests:runtests [test]',
            ],
    },
)
