.. _quickstart:

Quickstart
==========

This will guide you through the steps of getting up and running with your very own bot.

Installation
------------

First you will have to make sure you have brutal.

Installing brutal is simple with `pip <http://www.pip-installer.org/>`_::

    $ pip install brutal

Create a Bot
------------

Once you have brutal installed, you must start your new bot using the overlord.::

    $ brutal-overlord spawn <bot_name>

Where ``<bot_name>`` is the default nick of your new bot. This will create a new directory and populate it with the base
configuration that you will need.


Configuration
-------------

Once you have a bot, you will have to modify the ``<bot_name>/config.py`` file to get started.