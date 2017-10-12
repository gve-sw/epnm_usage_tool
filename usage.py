#!/usr/bin/env python
__author__ = "Michael Castellana"
__email__ = "micastel@cisco.com"
__status__ = "Development"

#import necessary libraries
import base64, getpass, requests, json, sys, time
from epnm import EPNM
from time import sleep
import csv
from xlrd import open_workbook

SLOTS = []

with open("slotList.csv", 'r') as my_file:
    reader = csv.reader(my_file)
    for row in reader:
        SLOTS.append(row[0])
    #print(SLOTS)


def make_get_req(auth, host, ext):
    headers={
        'content-type': "application",
        'authorization': "Basic "+auth,
        'cache-control': "no-cache",
    }
    url = "https://"+host+"/webacs/api/v1/data/"+ext+".json?"
    response = requests.request("GET", url, headers=headers, verify=False).json()
    return response

def make_get_req(auth, host, ext, filters):
    headers={
        'content-type': "application",
        'authorization': "Basic "+auth,
        'cache-control': "no-cache",
    }
    url = "https://"+host+"/webacs/api/v1/data/"+ext+".json?"+filters
    response = requests.request("GET", url, headers=headers, verify=False).json()
    return response

def get_inventory(auth, host):
    extension = 'Devices'
    id_list = []
    response = make_get_req(auth, host, extension)['queryResponse']['entityId']
    for item in response:
        id_list.append(str(item['$']))
    return id_list

def get_dev(auth, host, dev_id):
    extension = 'InventoryDetails/'+dev_id
    response = make_get_req(auth, host, extension)
    
    dev_pair = {}
    #print json.dumps(response, indent = 2)
    try:
        dev_type = str(response['queryResponse']['entity'][0]['devicesDTO'])
        dev_pair[dev_id] = dev_type
        return dev_pair
    except:
        return

def get_opt_dev(auth, host):
    response_list = []    
    extension = 'InventoryDetails'
    filters = "summary.productFamily=\"Optical Networking\""
    response = make_get_req(auth, host, extension, filters)

    id_list = response['queryResponse']['entityId']
    for dev in id_list:
        response_list.append(str(dev['$']))
    return response_list

def get_NCS2K_dev(auth, host):
    response_list = []    
    extension = 'InventoryDetails'
    filters = "full=true&summary.deviceType=startsWith(\"Cisco NCS 2\")&.maxResults=1"
    response = make_get_req(auth, host, extension, filters)

    id_list = response['queryResponse']['entityId']
    for dev in id_list:
        deviceID =  dev["$"]
        response_list.append(str(deviceID))
    return response_list

def determineCapacity(deviceType):
    if deviceType == 'Cisco NCS 2006':
        return 8
    if deviceType == 'Cisco NCS 2015':
        return 17
    # if deviceType == 'Cisco NCS 2002':
    return 3

def createDeviceModel(deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, utilization):
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

def get_NCS2KMOD_dev(auth, host, devID):
    response_list = []    
    extension = 'InventoryDetails/'+devID
    response = make_get_req(auth, host, extension)
    
    allDevices = []
    deviceList = response['queryResponse']['entity']

    for device in deviceList:
        summary = device['inventoryDetailsDTO']['summary']
        deviceID = summary['deviceId']
        deviceIP = summary['ipAddress']
        deviceName = summary['deviceName']
        deviceType = summary['deviceType']
        lineCards = {}
        slotUsage = 0
        capacity = determineCapacity(deviceType)
        modules = device['inventoryDetailsDTO']['modules']

        for module in modules['module']:
            productName = module["productName"]
            if productName in SLOTS:
                slotUsage += 1
                if productName in lineCards:
                    lineCards[productName] += 1
                else:
                    lineCards[productName] = 1

        utilization = float(slotUsage) / float(capacity)
        thisDevice = createDeviceModel(deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, utilization)
        allDevices.append(thisDevice)

    for each in allDevices:
        for k in each:
            v = each[k]
            print v
        print
        print
    return allDevices


def get_ip_map(auth, host, id_list):
    opt_list = {}
    pre_extension = 'InventoryDetails'
    for item in id_list:
        extension = pre_extension+item
        response = make_get_req(auth, host, extension)
        ip_addr = str(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['summary']['ipAddress'])
        opt_list[item]=ip_addr
    return opt_list



if __name__ == '__main__':
    #Disable warnings since we are not verifying SSL
    requests.packages.urllib3.disable_warnings()
    host_addr = 'tme-epnm'
    user = sys.argv[1]
    pwd = sys.argv[2]
    auth = base64.b64encode(user + ":" + pwd)

    ncs2k_list = get_NCS2K_dev(auth, host_addr)
    print ncs2k_list

    for dev in ncs2k_list:
        get_NCS2KMOD_dev(auth, host_addr, dev)

    #deviceList = get_dev(auth, host_addr, "7688694")

    # ref_out = '2k.csv'
    # with open(ref_out, 'w') as output:
    #     fieldnames = ['deviceID', 'deviceIP', 'deviceName', 'deviceType', 'lineCards', 'slotUsage', 'capacity', 'utilization']
    #     out_writer = csv.DictWriter(output, fieldnames=fieldnames)
    #     out_writer.writerow({'deviceID': 'Device ID', 'deviceIP':'Device IP', 'deviceName':'Device Name', 'deviceType':'Device Type', 'lineCards':'Line Cards', 'slotUsage':'Slot Usage', 'capacity':'Capacity', 'utilization':'Utilization'})
    #     print deviceList
    #     for device in deviceList:
    #         out_writer.writerow({'deviceID':device['deviceID'], 'deviceIP':device['deviceIP'], 'deviceName':device['deviceName'],'deviceType':device['deviceType'], 'lineCards':device['lineCards'], 'slotUsage':device['slotUsage'], 'capacity':device['capacity'], 'utilization':device['utilization']})















# def get_dev_det(auth, host,dev):
#     inv_dets = {}
    
#     url = "https://"+host+"/webacs/api/v1/data/InventoryDetails/"+dev+".json"
#     headers = get_headers(auth)
#     response = requests.request("GET", url, headers=headers, verify=False).json()
#     # print json.dumps(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['modules']['module'], indent=2)
#     # print len(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['modules']['module'])
#     dev_type = response['queryResponse']['entity'][0]['inventoryDetailsDTO']['summary']['deviceType']
#     mod_list = response['queryResponse']['entity'][0]['inventoryDetailsDTO']['modules']['module']
#     i = 0
#     for item in mod_list:
#         r_list = []
#         if item['equipmentType'] == 'MODULE': #and item['physicalLocation'] == 'SHELF':
#             # print json.dumps(item, indent=2)

#             i = i+1
#             r_list.append(str(dev_type))
#             r_list.append(str(item['productName']))

#             try:
#                 r_list.append(str(item['description']))
#             except:
#                 r_list.append(str('No Description Listed'))
            
#             try:
#                 r_list.append(str(item['physicalLocation']))
#             except:
#                 r_list.append(str('No Location Listed'))

        
#             inv_key = dev+' ['+str(i)+']'
#             inv_dets[inv_key] = r_list

#     # print '\n-------------------------'
#     # print str(i) + " Modules"
#     # print '-------------------------\n'

#     return inv_dets

#     # print json.dumps(response['queryResponse']['entity'][0]['inventoryDetailsDTO']['udiDetails'], indent=2)
#     