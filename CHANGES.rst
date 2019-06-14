LabCIRS changelog
=================

5.2 (2019-06-14)
----------------

* Added registration of new departments along with new reviewer and reporter accounts.
  Uses django-registration-redux_.
* Added setup.py which helps dealing with the local config file.
.. _django-registration-redux: https://github.com/macropin/django-registration


5.1 (2019-04-04)
----------------

* Reviewer can now change the name and password of users who are reporters for his departments.

5.0 (2019-03-09)
----------------

* Added support of multiple departments in one instalation. Script for joinig single department instances included.
* Added support for setting translation language, or deactivate translations (by setting supported
  languages to one). This functionality uses django-parler_.
* Dropped support for Django < 1.11
* ``manage.py`` shows default behaviour again
.. _django-parler: https://github.com/django-parler/django-parler

4.1.1 (2018-08-07)
------------------

* Updated used python modules (see requirements.txt).
* LabCIRS works now with Django 1.11 (only small modifications were necessary) - 1.9 still supported even if not recommended
* Updated Bootstrap to 4.1 (the navbar was slightly modified)
* Updated bundled JavaScript and CSS libraries

4.1.0 (2018-06-28)
------------------

* Added feedback functionality for reporter