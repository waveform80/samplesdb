=========
samplesdb
=========

Samples DB is an open-source web application for tracking the samples of lab
technicians, students, and other lab workers. It is current under development
with the aim of becoming a web-app hosted by the author upon completion, but
with the source code openly provided to anyone who wishes to run (for example)
a private copy (as may be required by labs handling sensitive or legally
sensitive samples).

The current state of the application is far from ready (it's not at the
"useful" stage yet), but anyone is free to play with it and provide feedback.
See the sections below for installation and usage instructions.


Installation
============

The basic pre-requisites for running a development copy of the system are
Python 2.6 or above, Python setuptools or distribute, and Python virtualenv.
The application is only tested on Linux but should probably work on Windows
or Mac OS X as well.

Once the pre-requisites are installed, open a shell and use the following
commands to configure a sandbox in which to install and run the application::

    $ virtualenv sandbox
    $ source sandbox/bin/activate
    $ git clone https://github.com/waveform80/samplesdb.git
    $ cd samplesdb
    $ python setup.py develop
    $ initialize_samplesdb_db development.ini

To run the application, use the following command::

    $ pserve development.ini

You should now be able to visit the application by accessing
http://localhost:8080/ in your favourite web browser.


Usage
=====

The database is initialized with a single administrative user with the
following credentials:

 * E-mail address: admin@example.com

 * Password: adminpass

Hopefully the user interface is sufficiently intuitive that no further
instructions are required, but if you feel anything can be improved in that
area, do feel free to contact me or raise an issue in github.


License
=======

This file is part of samplesdb.

samplesdb is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

samplesdb is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
samplesdb.  If not, see <http://www.gnu.org/licenses/>.

