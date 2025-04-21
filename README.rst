LabCIRS
=======

LabCIRS is a lightweight anonymous Critical Incident Reporting System (CIRS) developed for research laboratories/departments.

Background information can be found in
`A Laboratory Critical Incident and Error Reporting System for Experimental Biomedicine <https://doi.org/10.1371/journal.pbio.2000705>`_ published in `PLOS Biology <http://journals.plos.org/plosbiology/>`_

LabCIRS builds upon the `Django <http://www.djangoproject.com>`_ framework as a stand-alone web application and is not intended to be a reusable app.

A demo installation can be visited and tested at http://labcirs-demo.charite.de.

IMPORTANT
------------
As of version 6.0, LabCIRS works only with Python 3. Users of older versions have to create a new virtual environment with an appropriate Python version and install the correct version of mod_wsgi if LabCIRS is used with Apache.

Requirements
------------
- Python 3.12 (older versions of Python 3 might work but are not tested)
- Django 4.2 (older versions may work too but are not supported and not tested anymore)
- Pillow
- django-multiselectfield
- django-parler
- django-registration-redux
- any Django compatible database - tested in real life with MySQL and PostreSQL.
- any web server capable running WSGI applications - template for Apache 2.4 configuration is provided

(Required versions of Python modules are specified in requirements.txt)

Installation in Docker (**NEW**)
----------------------
LabCIRS can be installed in Docker. The installation is based on the `Dockerfile` and `compose.yml` files provided in the repository.
The installation is done in the following steps:
1. Clone the repository and create the `.env` file:
   ```bash
   git clone https://github.com/major-s/labcirs.git
   cd labcirs
   cp .env.example .env
   ```
2. Edit the `.env` file to set the desired configuration options.
3. If you want to use dockerized PostgreSQL, then copy the example `compose.override.yml` file:
   ```bash
   cp compose.override.dockerdb-example.yml compose.override.yml
   ```
4. Run the setup script to create the json configuration file:
   ```bash
   python setup.py
   ```
   The default database server is `db`, the database and database user `labcirsdb`, the database port is `5432`, the database password 
   the same you already set in the `.env` file. Set other variables as described below.
5. Create the TOS files if necessary. The TOS directory will be mountend in the container.
6. Build the image and run the Docker containers:
   ```bash
    docker compose up -d --build
    ```
7. Create the superuser (LabCIRS admin):
   ```bash
   docker compose exec app python manage.py createsuperuser
   ```
8. The application should be available at `http://localhost:8080` (or the port you specified in the `.env` file as LABCIRS_PROXY_PORT).

Installation
------------
Assuming usage of Apache, PostgreSQL and virtualenv on a Linux (Windows and MacOS should work too) machine, the installation steps are:

Install Python, virtualenv, PostgreSQL and Apache (with mod_wsgi) if not already present. On Ubuntu 18.04 following packages are required::

    apache2, libapache2-mod-wsgi-py3, postgresql, libpq-dev, python, python-dev, python-virtualenv

Create a database user, e.g.::

    sudo -u postgres createuser -P labcirs
    
Create a database owned by the user created in the previous step, e.g.::

    sudo -u postgres createdb -O labcirs labcirs
    
Create the main directory for all LabCIRS files::
 
    mkdir /opt/labcirs
  
and ``cd`` there.
    
Create a virtual environment (I usually do it in the main directory)::

    virtualenv venv_labcirs
    
Create ``static`` and ``media`` directories.

Make sure that the web server has write access to the ``media`` directory

Clone LabCIRS from GitHub and ``cd`` to its directory::

    git clone https://github.com/major-s/labcirs.git
    cd labcirs

Activate the virtual environment::

    source ../venv_labcirs/bin/activate
    
Install Django and required Python packages with pip::

    pip install -r requirements.txt
    
Install database adapter, e.g.::

    pip install psycopg2
    
Set the local configuration. This can be done either with ``setup.py``::

    python setup.py

or manually by copying the template, generation of the secret key and manual editing, e.g. with nano::

    cp labcirs/settings/local_config.json.template labcirs/settings/local_config.json
    python manage.py makesecretkey
    nano labcirs/settings/local_config.json

You should set following variables

- Variables for the database access, usually ``DB_ENGINE``, ``DB_NAME``, ``DB_USER`` and ``DB_PASSWORD``.
- If you intend to serve LabCIRS from a subdirectory and not from the root of your web server.
  then you have also to enter this subdirectory as ``ROOT_URL``.
- Add the domain of your web server to ``ALLOWED_HOSTS``.
- If your site uses multiple languages, set ``LANGUAGES`` ``PARLER*`` and ``ALL_LANGUAGES_MANDATORY_DEFAULT``.
- If users can register new departments, set all ``REGISTRATION*`` and ``ACCOUNT_ACTIVATION_DAYS``.

If registration is activated and users have to agree to any terms of service, you have to place a 
``tos_LANGUAGE.html`` file for every language used in the ``labcirs/tos`` directory. For English 
the file name will be ``tos_en.html``. See included ``tos_example.txt``.

Initialise the database::

    python manage.py migrate
     
Create superuser::

    python manage.py createsuperuser

Copy static files to the ``static`` directory

    python manage.py collectstatic
    
Copy the appropriate Apache configuration template:

- ``labcirs/labcirs.conf.root_template`` if you plan to serve LabCIRS from the root of the (virtual) web server.
- ``labcirs/labcirs.conf.template`` if you plan to serve LabCIRS from any subdirectory e.g. ``/labcirs``.

Make your configuration file accessible by Apache, activate it or include in the configuration.

Restart Apache

LabCIRS configuration
---------------------

Visit the URL you serve LabCIRS from

Login as the superuser you just created

Click on the admin button at the top of the page

Add new department. In the fresh installation, there are neither reporters nor reviewers. You can add
them by clicking on the green cross next to the corresponding dialogue. You will have to add the 
new users during this procedure too:
   
- a reporter - an account for anonymous reporting of incidents
- a reviewer - an account for analysis, copy-editing and publication of the incidents. 
  This account should have a valid email address specified.
       
In the admin interface go to the `LabCIRS configuration` and choose the automatically created 
configuration for the new department. Here you can specify where the users can get the information 
about the reporter login. Further, you can specify if email notifications should be sent to any 
reviewer upon creating new incidents. This function can only be activated if you set a valid 
``EMAIL_HOST`` in the local configuration file.

Update
-------

With activated virtual environment run::
    
    pip install -r requirements.txt
    python setup.py
    python manage.py migrate
    python manage.py collectstatic


Acknowledgements
----------------

The development of multitenant LabCIRS version was sponsored by the `Stiftung Charité <http://www.stiftung-charite.de>`_

Thanks to Claudia Kurreck, Nikolas Offenhauser, Ingo Przesdzing for ideas and testing. 

Users
-----

LabCIRS was created and used in the Department of Experimental Neurology at the Charité - University Medicine Berlin, Germany since 2014.
Since version 5 it is aviable for all research laboratories

If you use it and find it useful please give us a note.

Included software
-----------------

LabCIRS uses `Bootstrap <http://getbootstrap.com/>`_ and `jQuery <https://jquery.com>`_ with `DataTables <https://datatables.net>`_ which are included in this repository.
The copyright of these software packages is hold by its respective owners.

License
-------

Copyright (C) 2016-2025 Sebastian Major <sebastian.major@charite.de>

LabCIRS is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

LabCIRS is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with LabCIRS.
If not, see <https://www.gnu.org/licenses/>.