from __future__ import unicode_literals
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
import json
import traceback
from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer
import os.path
import csv

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required

from models import epnm_info as epnm_info
from controllers.rest_calls import EPNM_Usage as EPNM

import csv
from xlrd import open_workbook


SLOTS = []
TNC = []
LC = []
TWORU = []

# Reads in all neceassary static files
def set_constants():
    base = os.path.dirname(os.path.abspath(__file__))
    path = base+"/static/web_app/public/in_file/"
    with open(path+"slotList.csv", 'r') as slots:
        reader = csv.reader(slots)
        for row in reader:
            SLOTS.append(row[0])

    with open(path+"tnc_list.csv", 'r') as tnc:
        reader = csv.reader(tnc)
        for row in reader:
            TNC.append(row[0])

    with open(path+"revised_linecard_list.csv", 'r') as lc:
        reader = csv.reader(lc)
        for row in reader:
            LC.append(row[0])

    with open(path+"two_RU_linecard_list.csv", 'r') as two_ru:
        reader = csv.reader(two_ru)
        for row in reader:
            TWORU.append(row[0])


# ====================>>>>>>>> Templates <<<<<<<<====================
# Base template holder for all pages to build on
@login_required(login_url = '/web/login/')
def index(request, loc = '', dev = '', location = ''):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
    location_list = epnm_obj.get_locations()
    set_constants()
    return render(request, 'web_app/index.html', {'list':location_list})

# Display list of different locations for the site
@login_required(login_url = '/web/login/')
def home(request):
    return render(request, 'web_app/home.html')

@login_required(login_url = '/web/login/')
def main(request):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
    location_list = epnm_obj.get_locations()
    return render(request, 'web_app/main.html', {'list':location_list})

# Display list of devices by IP address associated with a location
@login_required(login_url = '/web/login/')
def location_landing(request, loc):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
    dev_list = epnm_obj.get_group_devs(loc)
    show = True
    if len(dev_list) == 0: 
        dev_list.append('No NCS2000 Devices at This Location')
        show = False
    return render(request, 'web_app/location_landing.html', {
        'arg_in':loc, 
        'dev_list':dev_list,
        'show':show
    })

# Display list of shelves and utilization information associated with a specific device
@login_required(login_url = '/web/login/')
def device_landing(request, dev):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'], SLOTS, TNC, LC, TWORU)

    report = epnm_obj.get_ncs2kmod_dev(dev)
    dev_info = report[0]
    dev_text = report[1] 

    multi = False
    show_act=False
    show_pass = False
    chas_num = 0

    if len(dev_info['active']) + len(dev_info['passive']) >1:
        multi=True
        chas_num=len(dev_info['active']) + len(dev_info['passive'])
    if len(dev_info['passive']) >0:
        show_pass=True
    if len(dev_info['active']) >0:
        show_act=True

    out_writer(dev_text, 'device')

    return render(request, 'web_app/device_landing.html', {
        'dev_info' : dev_info,
        'multi': multi,
        'show_act': show_act,
        'show_pass':show_pass,
        'chas_num':chas_num,
        'arg_in':dev, 
    })

# Display list of all devices associated with a location and all utilization information
@login_required(login_url = '/web/login/')
def location_dump(request, location):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'], SLOTS, TNC, LC, TWORU)
    dev_list = epnm_obj.get_group_devs(location)
    out_string= 'Inventory Report for '+location+'\n'
    arg_in=[]

    for dev in dev_list:
        template_dict={}
        report = epnm_obj.get_ncs2kmod_dev(dev)
        dev_info = report[0]
        dev_text = report[1]  

        multi = False
        show_act=False
        show_pass = False
        chas_num = 0

        if len(dev_info['active']) + len(dev_info['passive']) >0:
            multi=True
            chas_num=len(dev_info['active']) + len(dev_info['passive'])
        if len(dev_info['passive']) >0:
            show_pass=True
        if len(dev_info['active']) >0:
            show_act=True

        dev_dict={
        'dev_info': dev_info,
        'multi': multi,
        'show_act': show_act,
        'show_pass':show_pass,
        'chas_num':chas_num,
        }
        arg_in.append(dev_dict)
        out_string+='\n'+dev_text
    out_writer(out_string, 'location')
    return render(request, 'web_app/location_dump.html', {
        'arg_in': arg_in,
        'loc':location,
        })

# Display login page
def login_view(request):
    return render(request, 'web_app/login.html')

# Authenticate entered user credentials
def auth_view(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(request, username = username, password = password)
    if user is not None:
        login(request, user)
        return redirect('/web/')
        # Redirect to a success page.
    else:
        return render(request, 'web_app/login.html', {'error_msg':'Invalid Login'})
        # Return an 'invalid login' error message.

# Send email containing alarm information for a location
def send_group_email_view(request):
    if request.GET.get('mybtn'):
        location = str(request.GET.get('mybtn'))
        creds = epnm_info().get_info()
        epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
        base = os.path.dirname(os.path.abspath(__file__))
        download_url = base + '/static/web_app/public/out_file/location_report.txt'
        subject = "EPNM Usage Report for Devices in " + location
        epnm_obj.send_email('micastel@cisco.com',"epnm84@gmail.com", subject, download_url)#("steveyee@cisco.com", "epnm84@gmail.com", subject, download_url)
        
        redirect_url = "/web/alarms/" + location
        return redirect(redirect_url)

# Send email containing device specific information, attaches the static text file generated
def send_device_email_view(request):
    if request.GET.get('mybtn'):
        device = str(request.GET.get('mybtn'))
        print "Device is " + device
        creds = epnm_info().get_info()
        epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
        base = os.path.dirname(os.path.abspath(__file__))
        download_url = base + '/static/web_app/public/out_file/device_report.txt'
        subject = "EPNM Usage Report for Device " + device
        epnm_obj.send_email('micastel@cisco.com',"epnm84@gmail.com", subject, download_url)#"steveyee@cisco.com", "epnm84@gmail.com", subject, download_url)
        
        redirect_url = "/web/device/" + device
        return redirect(redirect_url)

# Create .txt file containing utilization information
def out_writer(text, label):
    base = os.path.dirname(os.path.abspath(__file__))
    output_file = base + '/static/web_app/public/out_file/'+label+'_report.txt'
    with open(output_file, "wb") as f:
        f.write(text)


