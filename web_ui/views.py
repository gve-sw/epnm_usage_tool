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



@login_required(login_url = '/web/login/')
def index(request, loc = '', dev = '', location = ''):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
    location_list = epnm_obj.get_locations()
    set_constants()
    return render(request, 'web_app/index.html', {'list':location_list})

@login_required(login_url = '/web/login/')
def home(request):
    return render(request, 'web_app/home.html')

@login_required(login_url = '/web/login/')
def main(request):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
    location_list = epnm_obj.get_locations()
    return render(request, 'web_app/main.html', {'list':location_list})


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

@login_required(login_url = '/web/login/')
def device_landing(request, dev):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'], SLOTS, TNC, LC, TWORU)

    report = epnm_obj.get_ncs2kmod_dev(dev)
    dev_info = report[0]
    dev_text = report[1] 

    # print dev_info
    #alarm_info = epnm_obj.get_alarms(dev)
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

    out_writer(dev_text)

    return render(request, 'web_app/device_landing.html', {
        'dev_info' : dev_info,
        'multi': multi,
        'show_act': show_act,
        'show_pass':show_pass,
        'chas_num':chas_num
        # 'arg_in':dev, 
        # 'alarm_info':alarm_info,
        # 'download_link':output_file,
    })


@login_required(login_url = '/web/login/')
def location_dump(request, location):
    creds = epnm_info().get_info()
    epnm_obj = EPNM(creds['host'], creds['user'], creds['password'], SLOTS, TNC, LC, TWORU)
    dev_list = epnm_obj.get_group_devs(location)

    dev_info_dump = []
    dev_text_dump = []
    multi_dump = []
    show_act_dump = []
    show_pass_dump = []
    chas_num_dump = []

    

    for dev in dev_list:
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

        dev_info_dump.append(dev_info)
        dev_text_dump.append(dev_text)
        multi_dump.append(multi)
        show_act_dump.append(show_act)
        show_pass_dump.append(show_pass)
        chas_num_dump.append(chas_num)

    print dev_info_dump
    print 'end'



    # d_string = []
    # d_string.append('+++++ ' + location + ' Alarm Summary +++++')
    # for device in alarm_list:
    #     d_string.append('Device ' + device)
    #     for alarm in alarm_list[device]:
    #         d_string.append('\tAlarmID: ' + alarm)
    #         for key in alarm_list[device][alarm]:
    #             d_string.append('\t' + key + ':' + str(alarm_list[device][alarm][key])) 
    #         d_string.append('\n')
    #     d_string.append('\n')
    # group_writer(alarm_list)

    # base = os.path.dirname(os.path.abspath(__file__))
    # output_file = base + '/out_files/alarm_report.csv'

    # alarm_breakdown={}
    # total_alarms = 0
    # for item in alarm_list:
    #     for k in alarm_list[item]:
    #         for v in alarm_list[item][k]:
    #             if v=='Severity':
    #                 sev = alarm_list[item][k][v]
    #                 total_alarms += 1
    #                 if sev not in alarm_breakdown:
    #                     alarm_breakdown[sev]=1
    #                 else:
    #                     alarm_breakdown[sev]+=1

    return render(request, 'web_app/location_dump.html', {
        'dev_info' : dev_info_dump,
        'multi': multi_dump,
        'show_act': show_act_dump,
        'show_pass':show_pass_dump,
        'chas_num':chas_num_dump,
        'arg_in':location,
        })


def login_view(request):
    return render(request, 'web_app/login.html')

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

def send_group_email_view(request):
    if request.GET.get('mybtn'):
        location = str(request.GET.get('mybtn'))
        creds = epnm_info().get_info()
        epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
        if epnm_obj.get_group_alarms(location) != {}:
            print "found"
            base = os.path.dirname(os.path.abspath(__file__))
            download_url = base + '/static/web_app/public/out_file/alarm_report.csv'
            subject = "EPNM Alarm Report for Devices in " + location
            epnm_obj.send_email('micastel@cisco.com',"epnm84@gmail.com", subject, download_url)#("steveyee@cisco.com", "epnm84@gmail.com", subject, download_url)
        redirect_url = "/web/alarms/" + location
        return redirect(redirect_url)

def send_device_email_view(request):
    if request.GET.get('mybtn'):
        device = str(request.GET.get('mybtn'))
        print "Device is " + device
        creds = epnm_info().get_info()
        epnm_obj = EPNM(creds['host'], creds['user'], creds['password'])
        if epnm_obj.get_alarms(device) != {}:
            base = os.path.dirname(os.path.abspath(__file__))
            download_url = base + '/static/web_app/public/out_file/alarm_report.csv'
            subject = "EPNM Alarm Report for Device " + device
            epnm_obj.send_email('micastel@cisco.com',"epnm84@gmail.com", subject, download_url)#"steveyee@cisco.com", "epnm84@gmail.com", subject, download_url)
        redirect_url = "/web/device/" + device
        return redirect(redirect_url)

def group_writer(alarm_list):
    base = os.path.dirname(os.path.abspath(__file__))
    output_file = base + "/static/web_app/public/out_file/alarm_report.csv"

    with open(output_file, 'wb') as alarm_report:
        thisWriter = csv.writer(alarm_report)
        thisWriter.writerow(['Failure Source', 'Key', 'Acknowledgment Status', 'Time Stamp Created', 'Notes', 'Last Updated At', 'Description', 'Severity', ])
        for device_ip in alarm_list:
            for alarm in alarm_list[device_ip]:
                device_string = []
                device_string.append(device_ip)
                device_string.append(alarm)
                for key in alarm_list[device_ip][alarm]:                        
                    if key != "FailureSource":
                        device_string.append(alarm_list[device_ip][alarm][key])
                thisWriter.writerow(device_string)
    return output_file


def out_writer(text):
    base = os.path.dirname(os.path.abspath(__file__))
    output_file = base + '/static/web_app/public/out_file/usage_report.txt'
    with open(output_file, "wb") as f:
        f.write(text)



def download(request, path):
    filename = "usage_report.txt"
    content = 'any string generated by django'
    return HttpResponse(content, content_type = 'text/plain')

