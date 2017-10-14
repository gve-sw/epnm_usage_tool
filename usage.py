#!/usr/bin/env python
__author__ = "Michael Castellana and Steven Yee"
__email__ = "micastel@cisco.com and steveyee@cisco.com"
__status__ = "Development"

#import necessary libraries
import base64, getpass, requests, json, sys, time
from epnm import EPNM
from time import sleep
import csv
from xlrd import open_workbook

SLOTS = []
TNC = []
LC = []

with open("slotList.csv", 'r') as slots:
    reader = csv.reader(slots)
    for row in reader:
        SLOTS.append(row[0])

with open("tnc_list.csv", 'r') as tnc:
    reader = csv.reader(tnc)
    for row in reader:
        TNC.append(row[0])

with open("lincard_list.csv", 'r') as lc:
    reader = csv.reader(lc)
    for row in reader:
        LC.append(row[0])

def get_headers(auth, content_type = "application", cache_control = "no-cache"):
    headers={
        'content-type': content_type,
        'authorization': "Basic "+ auth,
        'cache-control': cache_control,
    }
    return headers

def get_response(url, headers, requestType = "GET", verify = False):
    return requests.request(requestType, url, headers=headers, verify = verify).json()

def make_get_req(auth, host, ext, filters = ""):
    headers = get_headers(auth)
    url = "https://"+host+"/webacs/api/v1/data/"+ext+".json?"+filters
    return get_response(url, headers, requestType = "GET", verify = False)

def get_device_ID_list(response):
    id_list = []
    for item in response:
        id_list.append(str(item['$']))
    return id_list

def get_inventory(auth, host):
    """ Queries all registered Guests"""
    extension = 'Devices'
    response = make_get_req(auth, host, extension)
    response =  response['queryResponse']['entityId']
    id_list = get_device_ID_list(response)
    return id_list

def get_single_device(auth, host, device_id):
    extension = 'InventoryDetails/' + device_id
    response = make_get_req(auth, host, extension)
    dev_pair = {}
    try:
        dev_type = str(response['queryResponse']['entity'][0]['inventoryDetailsDTO'])
        dev_pair[device_id] = dev_type
        return dev_pair
    except:
        raise ValueError("Device " + str(device_id) + " not found")

def get_all_optical_device_ids(auth, host):
    extension = 'InventoryDetails'
    filters = "summary.productFamily=\"Optical Networking\""
    response = make_get_req(auth, host, extension, filters)
    response = response['queryResponse']['entityId']
    id_list = get_device_ID_list(response)
    return id_list

def determine_capacity(physicalLocation):
    if physicalLocation == 'SHELF':
        return 6
    location = physicalLocation[0:6]
    if 'SHELF-' == location:
        productFamily = physicalLocation[-4:]
        if '-M2]' == productFamily:
            return 2
        if '-M6]' == productFamily:
            return 6
        if 'M15]' == productFamily:
            return 15
        raise ValueError("SHELF")
    #****************************************
    #Not worrying about p-shelf at the moment
    # if 'PSHELF' == location:
    #     productFamily = physicalLocation[-9:]
    #     # if '-2RU]' == productFamily:
    #     #     return 2
    #     if 'F-MF-6RU]' == productFamily:
    #         return 14
    #     if 'MF10-6RU]' == productFamily:
    #         return 10
    #     raise ValueError("PSHELF")
    #****************************************
    return 0

def create_device_model(deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, utilization):
    device = {
        'deviceID' : deviceID,
        'deviceIP' : deviceIP,
        'deviceName' : deviceName,
        'deviceType' : deviceType,
        'lineCards' : lineCards,
        'slotUsage' : slotUsage,
        'capacity' : capacity,
        'utilization' : utilization
    }
    return device

def print_device_list_capacity_summary(allDevices):
    for device in allDevices:
        for property in device:
            value = device[property]
            print value
        print

def get_NCS2K_list(auth, host):
    id_list = []
    extension = 'InventoryDetails'
    filters = "summary.deviceType=startsWith(\"Cisco NCS 2\")"
    response = make_get_req(auth, host, extension, filters)
    for item in response['queryResponse']['entityId']:
        id_list.append(item['$'])
    return id_list

def get_NCS2KMOD_dev(auth, host, devID):
    allDevices = []
    # extension = 'InventoryDetails'
    # filters = ".full=true&summary.deviceType=startsWith(\"Cisco NCS 2\")"
    # response = make_get_req(auth, host, extension, filters)
    
    #extension = 'InventoryDetails/7688694'
    extension = 'InventoryDetails/'+devID
    response = make_get_req(auth, host, extension)

    deviceList = response['queryResponse']['entity']

    for device in deviceList:
        summary = device['inventoryDetailsDTO']['summary']
        deviceID = summary['deviceId']
        deviceIP = summary['ipAddress']
        deviceName = summary['deviceName']
        deviceType = summary['deviceType']
        lineCards = {}

        chassis_list=[]
        chassis_parings = {}

        chasses = []
        slotUsage = 0
        capacity = 0
        modules = device['inventoryDetailsDTO']['modules']

        validChassis = False
        shelf_count = 1
        tnc_cap = 0
        chassis = ''

        for module in modules['module']:
            #print 'chassis: '+str(chasses)

            productName = module["productName"]
            if "physicalLocation" in module:
                
                physicalLocation = module["physicalLocation"]

                chassisCapacity = determine_capacity(physicalLocation)
                if chassisCapacity==2: 
                    tnc_cap = 1
                    chassis = 'NCS2002'
                if chassisCapacity==6: 
                    tnc_cap = 2
                    chassis = 'NCS2006'
                if chassisCapacity==15: 
                    tnc_cap = 2
                    chassis = 'NCS2015'


                if physicalLocation in chasses:
                    #print "Already counted: " + physicalLocation
                    #print chasses.count(physicalLocation)
                    chassis = chassis_list[chasses.index(physicalLocation)]
                    validChassis = True
                else:
                    chassisCapacity = determine_capacity(physicalLocation)
                    #print physicalLocation+' : '+str(chassisCapacity)
                    if chassisCapacity > 0:
                        validChassis = True
                        capacity += chassisCapacity
                        chasses.append(physicalLocation)
                        chassis = chassis+'['+physicalLocation[0:7]+']'
                        shelf_count +=1
                        chassis_list.append(chassis)
                        chassis_parings[chassis] = [0,tnc_cap,0,chassisCapacity] #--> [TNC, LC]
                        

            if validChassis == True:
                if productName in LC:
                    #print '********* IN ********'
                    slotUsage += 1
                    chassis_parings[chassis][2] +=1
                    if productName in lineCards:
                        lineCards[productName] += 1
                    else:
                        lineCards[productName] = 1
                if productName in TNC:
                    #print '********* IN ********'
                    slotUsage += 1
                    chassis_parings[chassis][0] +=1

            # print json.dumps(module, indent=2)
            # print 'slot usage: '+str(slotUsage)
            # print "\n++++++++++++++++++++++++++++++\n\n"

            validChassis = False
            chassis = 'null'
            chassisCapacity = 0
        
        # print
        # print chassis_list
        # print deviceType
        # print 
        print "++++++ Summary for "+deviceName+" ++++++"
        print "\tDevice ID: "+str(deviceID)
        print "\tAddress: "+str(deviceIP)
        if len(chasses)>1:
            print "\n\tMulti Chassis Rack - "+str(len(chasses))+" Shelves"
        else:
            print "\n\tSingle Chassis Rack"
        for dev in chassis_parings:
            print "\t"+dev+":"
            tnc_util = (float(chassis_parings[dev][0])/chassis_parings[dev][1])*100
            lc_util = (float(chassis_parings[dev][2])/chassis_parings[dev][3])*100
            print "\t\tControllers: "+str(chassis_parings[dev][0])+"/"+str(chassis_parings[dev][1])+" Slots Populated - "+str(format(tnc_util, '.0f'))+"% Utilization"
            print "\t\tService Cards: "+str(chassis_parings[dev][2])+"/"+str(chassis_parings[dev][3])+" Slots Populated - "+str(format(lc_util, '.0f'))+"% Utilization"
        print
        utilization = float(slotUsage) / float(capacity)
        thisDevice = create_device_model(deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, utilization)
        allDevices.append(thisDevice)

    #print_device_list_capacity_summary(allDevices)
    return allDevices

def get_ip_map(auth, host, id_list):
    opt_list = {}
    pre_extension = 'InventoryDetails/'
    for item in id_list:
        extension = pre_extension + item
        response = make_get_req(auth, host, extension)
        print response
        ip_addr = str(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['summary']['ipAddress'])
        opt_list[item]=ip_addr

    return opt_list


if __name__ == '__main__':
    #Disable warnings since we are not verifying SSL
    requests.packages.urllib3.disable_warnings()
    host_addr = 'tme-epnm'
    # user = raw_input("User: ")
    # pwd = getpass.getpass("Password: ")

    #use above for taking in arguments- i got lazy so i didnt feel like typing it each time
    #i just took the commands at run time
    user = sys.argv[1]
    pwd = sys.argv[2]
    auth = base64.b64encode(user + ":" + pwd)


    deviceList = get_NCS2K_list(auth, host_addr)
    #deviceList=['7688693']
    for dev in deviceList:
        get_NCS2KMOD_dev(auth, host_addr, dev)

    # ref_out = '2k_update.csv'
    # with open(ref_out, 'w') as output:
    #     fieldnames = ['deviceID', 'deviceIP', 'deviceName', 'deviceType', 'lineCards', 'slotUsage', 'capacity', 'utilization']
    #     out_writer = csv.DictWriter(output, fieldnames=fieldnames)
    #     out_writer.writerow({'deviceID': 'Device ID', 'deviceIP':'Device IP', 'deviceName':'Device Name', 'deviceType':'Device Type', 'lineCards':'Line Cards', 'slotUsage':'Slot Usage', 'capacity':'Capacity', 'utilization':'Utilization'})
    #     for device in deviceList:
    #         out_writer.writerow({'deviceID':device['deviceID'], 'deviceIP':device['deviceIP'], 'deviceName':device['deviceName'],'deviceType':device['deviceType'], 'lineCards':device['lineCards'], 'slotUsage':device['slotUsage'], 'capacity':device['capacity'], 'utilization':device['utilization']})
    # 