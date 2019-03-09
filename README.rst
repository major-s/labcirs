LabCIRS
=======

LabCIRS is a lightweight anonymous Critical Incident Reporting System (CIRS) developed for research laboratories/departments.

Background informations can be found in
`A Laboratory Critical Incident and Error Reporting System for Experimental Biomedicine <https://doi.org/10.1371/journal.pbio.2000705>`_ published in `PLOS Biology <http://journals.plos.org/plosbiology/>`_

LabCIRS builds upon the `Django <http://www.djangoproject.com>`_ framework as a stand alone web application and is not intended to be a reusable app.

A demo installation can be visited and tested at http://labcirs-demo.charite.de.

Requirements
------------
- Python 2.7
- Django 1.11 (older versions may work too but are not tested any more)
- Pillow 5.2.0
- django-multiselectfield 0.1.8
- django-parler 1.9.2
- any Django compatible database - tested in real life with MySQL and PostreSQL.
- any web server capable running WSGI applications - template for Apache 2.4 configuration is provided

Installation
------------
Assuming usage of Apache, PostgreSQL and virtualenv on a Linux machine the installation steps are:

1. Install Python, virtualenv, PostgreSQL and Apache (with mod_wsgi) if not already present. On Ubuntu 14.04 following packages are required:

  .. code-block:: bash

    apache2, libapache2-mod-wsgi, postgresql, libpq-dev, python, python-dev, python-virtualenv

2. Create a database user, e.g.

  .. code-block:: bash

    sudo -u postgres createuser -P labcirs
    
3. Create a database owned by the user created in the previous step, e.g.

  .. code-block:: bash

    sudo -u postgres createdb -O labcirs labcirs
    
4. Create the main directory for all LabCIRS files, e.g.
  
  .. code-block:: bash
  
      mkdir /opt/labcirs
  
  and ``cd`` there.
    
5. Create virtual environment (I usually do it in the main directory), e.g.

  .. code-block:: bash

    virtualenv venv_labcirs
    
6. Create ``static`` and ``media`` directories.

7. Make sure that the web server has write access to the ``media`` directory

8. Clone LabCIRS from GitHub and ``cd`` to its directory 

9. Activate the virtual environment, e.g.

  .. code-block:: bash

    source ../venv_labcirs/bin/activate
    
10. Install Django and required Python packages with pip:

  .. code-block:: bash

    pip install -r requirements.txt
    
11. Install database adapter, e.g.

  .. code-block:: bash

    pip install psycopg2
    
12. Copy the template of local config file:

  .. code-block:: bash

    cp labcirs/settings/local_config.json.template labcirs/settings/local_config.json
    
13. Generate the ``SECRET_KEY`` with provided management command

  .. code-block:: bash

    python manage.py makesecretkey
    
14. Edit the local config file
     * enter the values for the database access, usually ``DB_ENGINE``, ``DB_NAME``, ``DB_USER`` and ``DB_PASSWORD``.
     * If you intend to serve LabCIRS from a subdirectory and not from the root of your web server 
       then you have also to enter this subdirectory as ``ROOT_URL``.
     * Add the domain of your web server to ``ALLOWED_HOSTS``

15. Initialise the database :

  .. code-block:: bash

    python manage.py migrate
     
16. Create superuser:

  .. code-block:: bash

    python manage.py createsuperuser
    
17. Copy the appropriate Apache configuration template:
     * ``labcirs/labcirs.conf.root_template`` if you plan to serve LabCIRS from the root of the (virtual) web server.
     * ``labcirs/labcirs.conf.template`` if you plan to serve LabCIRS from any subdirectory e.g. ``/labcirs``.

18. Make your configuration file accessible by Apache, activate it or include in the configuration.

19. Restart Apache

LabCIRS configuration
---------------------

1. Visit the URL you serve LabCIRS from

2. Login as the superuser you just created

3. Click on the admin button at the top of the page

4. Add new department. In fresh installation there are neither reporters nor reviewers. You can add
   them by clicking on the green cross next to the corresponding dialogue. You will have to add the 
   new users during this procedure too:
   
   * a reporter - an account for anonymous reporting of incidents
   * a reviewer - an account for analysis, copy-editing and publication of the incidents. 
     This account should have a valid email address specified.
       
5. In the admin interface go to the `LabCIRS configuration` and choose the automatically created 
   configuration for the new department. Here you can specify where the users can get the information 
   about the reporter login. Further you can specify if email notifications should be sent to any 
   reviewer upon creation of new incidents. This function can only be activated if you set a valid 
   ``EMAIL_HOST`` in the local configuration file.

Update
-------

Check which keys are missing in the local configuration file ``local_config.json``, add them and
set values you need.

If you want to join multiple single department installations use ``import_dept_to_org.py`` from the
python shell after succesful update.

Acknowledgements
----------------

Current development of LabCIRS is sponsored by the `Stiftung Charité <http://www.stiftung-charite.de>`_

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

Copyright (C) 2016-2019 Sebastian Major <sebastian.major@charite.de>

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