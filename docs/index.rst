.. brutal documentation master file, created by
   sphinx-quickstart on Mon Apr 15 20:52:19 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

brutal: a multi-network asynchronous chat bot framework
==================================

Release v\ |version|. - ALPHA release


There are multiple ways to write a chat bot in python, but most thread out to support user code and mix and match client
libs to support multiple protocols. brutal is an attempt to change this using the twisted framework. All network code is
written using twisted libraries for native async support.


Code
--------

brutal is actively developed on GitHub. You can find the repo `here <https://github.com/Netflix/brutal>`_.


Feature Support
---------------

- IRC
- XMPP
- Everything runs async by default.
- Thread pool support exists for explicitly defined blocking code


User Guide
----------

.. toctree::
   :maxdepth: 2

   quickstart
   plugins


.. _`apache2`:

License
----------------

.. include:: ../LICENSE


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

