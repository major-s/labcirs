=======
LabCIRS
=======

LabCIRS is a lightweight anonymous Critical Incident Reporting System (CIRS) developed for research laboratories/departments.

Background informations can be found in
`A Laboratory Critical Incident and Error Reporting System for Experimental Biomedicine <https://doi.org/10.1371/journal.pbio.2000705>`_ published in `PLOS Biology <http://journals.plos.org/plosbiology/>`_

LabCIRS builds upon the `Django <http://www.djangoproject.com>`_ framework as a stand alone web application and is not intended to be a reusable app.

A demo installation can be visited and tested at http://labcirs.charite.de.

Requirements
------------
- Python 2.7
- Django 1.11 (1.9 and 1.10 work too but are not recommended)
- Pillow 5.2.0
- django-multiselectfield 0.1.8
- django-parler 1.9.2
- any Django compatible database - tested in real life with MySQL and PostreSQL.
- any web server capable running WSGI applications - a template for Apache 2.4 configuration is provided

Installation
------------
Assuming usage of Apache, PostgreSQL and virtualenv on a Linux machine the installation steps are:

1. Install Python, virtualenv, PostgreSQL and Apache (with mod_wsgi) if not already present. On Ubuntu 14.04 following packages are required:
    ``apache2, libapache2-mod-wsgi, postgresql, libpq-dev, python, python-dev, python-virtualenv``
2. Create a database user, e.g.
    ``sudo -u postgres createuser -P labcirs``
3. Create a database owned by the user created in the previous step, e.g.
    ``sudo -u postgres createdb -O labcirs labcirs``
4. Create the main directory for all LabCIRS files, e.g.
    ``mkdir /opt/labcirs`` and cd there.
5. Create virtual environment (I usually do it in the main directory), e.g.
    ``virtualenv venv_labcirs``
6. Create ``static`` and ``media`` directories.
7. Make sure that the web server has write access to the ``media`` directory
8. Clone LabCIRS from GitHub
9. cd to LabCIRS directory
10. Activate the virtual environment, e.g.
     ``source ../venv_labcirs/bin/activate``
11. Install Django and required Python packages with pip:
     ``pip install -r requirements.txt``
12. Install database adapter, e.g.
     ``pip install psycopg2``
13. Copy the template of local config file:
     ``cp labcirs/settings/local_config.json.template labcirs/settings/local_config.json``
14. Generate the ``SECRET_KEY`` with provided management command
     ``python manage.py makesecretkey``
15. Edit the local config file
     a) enter the values for the database access, usually ``DB_ENGINE``, ``DB_NAME``, ``DB_USER`` and ``DB_PASSWORD``.
     b) If you intend to serve LabCIRS from a subdirectory and not from the root of your web server then you have also to enter this subdirectory as ``ROOT_URL``.
     c) Add the domain of your web server to ``ALLOWED_HOSTS``
16. Initialise the database :
     ``python manage.py migrate`` 
17. Create superuser:
     ``python manage.py createsuperuser``
18. Copy and edit ``labcirs/labcirs.conf.template`` and make a symlink to your final ``labcirs.conf`` in ``/etc/apache2/conf-available``
19. Enable your config, e.g.
     ``sudo a2enconf labcirs``
20. Restart apache

LabCIRS configuration
---------------------

1. Visit the URL you serve LabCIRS from
2. Login as the superuser you just created
3. Click on the admin button at the top of the page
4. Add two users:
    a) a reporter - an account for anonymous reporting of incidents
    b) a reviewer - an account for analysis, copyediting and publication of the incidents. This account should have a valid email address specified.
5. This users needs specific permissions:
    a) reporter
        i) "can add critical incident"
    b) reviewer
        i) "can add user"
        ii) "can change user"
        iii) "can change critical incident"
        iv) "can add LabCIRS configuration"
        v) "can change LabCIRS configuration"
        vi) "can add publishable incident"
        vii) "can change publishable incident"
6. If you plan to use multiple reviewer account then you should create a group with appropriate permissions and add all users with the reviewer role to this group.
7. In the admin interface go to the ``LabCIRS configuration`` and add a new configuration (only one can be used). Here you can specify where the users can get the information about the reporter login. Further you can specify if email notifications should be sent to any reviewer upon creation of new incidents. This function can only be activated if you set a valid ``EMAIL_HOST`` in the local configuration file.

Acknowledgments
---------------

Current development of LabCIRS is sponsored by the `Stiftung Charité <http://www.stiftung-charite.de>`_

Users
-----

LabCIRS was created and is used in the Department of Experimental Neurology at the Charité - University Medicine Berlin, Germany since 2014.

If you use it and find it usefull please give us a note.

Included software
-----------------

LabCIRS uses `Bootstrap <http://getbootstrap.com/>`_ and `jQuery <https://jquery.com>`_ with `DataTables <https://datatables.net>`_ which are included in this repository.
The copyright of these software packages is hold by its respective owners.

License
-------

Copyright (C) 2016-2018 Sebastian Major <sebastian.major@charite.de>

LabCIRS is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

LabCIRS is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with LabCIRS.
If not, see <http://www.gnu.org/licenses/old-licenses/gpl-2.0>.