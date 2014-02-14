from distutils.core import setup
from os.path import dirname, realpath
from os import sep
from setuptools import find_packages
from setuptools.command.test import test as TestCommand
import sys


pip_requirements = 'requirements.txt'
test_requirements = 'tests/requirements.txt'


class Tox(TestCommand):
    """The test command should install and then run tox.

    Based on http://tox.readthedocs.org/en/latest/example/basic.html
    """
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import tox  # Import here, because outside eggs aren't loaded.
        sys.exit(tox.cmdline(self.test_args))


setup(
    # Basic metadata
    name='drf-toolbox',
    version=open('VERSION').read().strip(),
    author='FeedMagnet',
    author_email='tech@feedmagnet.com',
    url='https://github.com/feedmagnet/drf-toolbox',

    # Additional information
    description='A collection of useful functionality on top of '
                'Django REST Framework.',
    license='New BSD',
    zip_safe=False,

    # How to do the install
    install_requires=open(pip_requirements, 'r').read().strip().split('\n'),
    provides=[
        'drf_toolbox',
    ],
    packages=[i for i in find_packages() if i.startswith('drf_toolbox')],

    # How to do the tests
    tests_require=['tox'],
    cmdclass={'test': Tox },

    # Data files
    package_data={
        'drf_toolbox': ['.VERSION'],
    },

    # PyPI metadata
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development',
    ],
)
