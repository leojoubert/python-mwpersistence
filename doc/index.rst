MediaWiki persistence
=====================

This library provides a set of utilities for interacting tracking the
persistence of content through the history of pages in MediaWiki.  The most
salient feature of this library is the :class:`mwpersistence.DiffState` that
tracks changes in the state of page by applying diff operations sequentially.

There's also a set of :mod:`~mwpersistence.utilities` provided that will
generate diffs and persistence statistics from MediaWiki XML dumps.

Contents
--------
.. toctree::
    :maxdepth: 1

    state
    functions
    utilities

Author
------
* Aaron Halfaker -- https://github.com/halfak

.. code::

  MIT LICENSE

  Copyright (c) 2015 Aaron Halfaker <aaron.halfaker@gmail.com>

  Permission is hereby granted, free of charge, to any person
  obtaining a copy of this software and associated documentation
  files (the "Software"), to deal in the Software without
  restriction, including without limitation the rights to use,
  copy, modify, merge, publish, distribute, sublicense, and/or
  sell copies of the Software, and to permit persons to whom
  the Software is furnished to do so, subject to the following
  conditions:

  The above copyright notice and this permission notice shall
  be included in all copies or substantial portions of the
  Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
  KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
  WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
  PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
  OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
  OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
