import os
import sys
from setuptools import setup, find_packages

setup(
    name='brutal-bot',
    version='0.1.0',

    description='brutal-bot, another awful chat bot.',

    author='Corey Bertram',
    author_email='corey@qr7.com',

    scripts=['brutal/bin/brutal-overlord.py',],

    include_package_data=True,
    packages = find_packages(),

    install_requires = [],

    #zip_safe=False,
)