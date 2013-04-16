#!/usr/bin/env python

import brutal

from setuptools import setup, find_packages

setup(
    name='brutal',
    version=brutal.__version__,

    description='a multi-network asynchronous chat bot framework using twisted.',
    long_description=open('README.rst').read(),

    author='Corey Bertram',
    author_email='corey@qr7.com',

    url='https://github.com/q/brutal',

    scripts=['brutal/bin/brutal-overlord.py', ],

    include_package_data=True,
    packages=find_packages(),

    license=open('LICENSE').read(),

    install_requires=[
        'Twisted >= 12.1.0',
    ],

    keywords='twisted',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Framework :: Twisted',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Topic :: Communications :: Chat',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'License :: OSI Approved :: Apache Software License',
    ],
)
