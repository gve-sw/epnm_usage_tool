**EPNM Alarms Application**

This application uses the Evolved Programmable Network Manager (EPNM) Rest API to query unresolved alarm information within the network. These alarm queries can be grouped by location defined groups, or can be specific to an individual device. The application will present the user with an alarm report in the browser, and the user can download the report to a .txt for future review.

The HTML user interface works better in Chrome and Firefox.

Contacts:

* Michael Castellana (micastel@cisco.com)
* Steven Yee (steveyee@cisco.com)
* Jason Mah (jamah@cisco.com)
* Santiago Flores (sfloresk@cisco.com)



**Source Installation**

Usually will be something like below:

As this is a Django application you will need to either integrate the application in your production environment or you can get it operational in a virtual environment on your computer/server. In the distribution is a requirements.txt file that you can use to get the package requirements that are needed. The requirements file is located in the root directory of the distribution.

It might make sense for you to create a Python Virtual Environment before installing the requirements file. For information on utilizing a virtual environment please read http://docs.python-guide.org/en/latest/dev/virtualenvs/. Once you have a virtual environment active then install the packages in the requirements file.

`(virtualenv) % pip install -r requirements.txt
`

There are two ways to run the application. The second way is recommended as it will dynamically update if you make changes to the code.
1) Execute in the root directory of the distribution:
 - python manage.py makemigrations
 - python manage.py migrate
 - python manage.py runserver 127.0.0.1:5002

2) The root directory contains a shell script that will perform the three commands in step 1.
To run this script and start the application with one command, enter the following in the root directory:
 - ./web_start.sh
This will run the web server and content can be accessed by navigating to 127.0.0.1:5002/web/ in your browser.

Log in with username: admin and password: cisco123

**Known Issues**

The EPNM Rest API can be slow. It sometimes helps to VPN into RTP before running the application.