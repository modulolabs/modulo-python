#!/usr/bin/python

from setuptools import setup

# To create a new tarball on github, run:
#    git tag 0.1 -m "Creating tag for version 0.1"
#    git push --tags origin master
#
# See http://peterdowns.com/posts/first-time-with-pypi.html for more pypi info

setup(name='modulo-python',
    version='1.0',
    description='Python support for Modulo hardware',
    url='https://github.com/integer-labs/modulo-python',
    download_url = 'https://github.com/integer-labs/modulo-python/tarball/0.1',
    author='Erin Tomson',
    author_email='erin@integerlabs.net',
    packages=['modulo'],
    entry_points={
        'console_scripts': [
            'modulo-list=modulo.scripts:list'
        ]
    },
    install_requires=['pyserial']
    )

