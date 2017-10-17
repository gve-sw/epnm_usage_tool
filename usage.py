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
TWORU = []

with open("slotList.csv", 'r') as slots:
    reader = csv.reader(slots)
    for row in reader:
        SLOTS.append(row[0])

with open("tnc_list.csv", 'r') as tnc:
    reader = csv.reader(tnc)
    for row in reader:
        TNC.append(row[0])

with open("revised_linecard_list.csv", 'r') as lc:
    reader = csv.reader(lc)
    for row in reader:
        LC.append(row[0])

with open("two_RU_linecard_list.csv", 'r') as two_ru:
    reader = csv.reader(two_ru)
    for row in reader:
        TWORU.append(row[0])

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

def make_shelf_info(shelfTypeRaw, capacity, chassisType, controllerCapacity):
    if shelfTypeRaw == 0:
        shelfType = "active"
    elif shelfTypeRaw == 1:
        shelfType = "passive"
    else:
        shelfType = shelfTypeRaw
    return {
        'shelfType' : shelfType,
        'capacity' : capacity,
        'chassisType' : chassisType,
        'controllerCapacity' : controllerCapacity
    }

def determine_shelf_info(physicalLocation):
    if physicalLocation == 'SHELF':
        return make_shelf_info(0,6,'NCS2006',2)
    location = physicalLocation[0:6] #0==active, 1==passive
    if 'SHELF-' == location:
        productFamily = physicalLocation[-4:]
        if '-M2]' == productFamily:
            return make_shelf_info(0,2,'NCS2002',1)
        if '-M6]' == productFamily:
            return make_shelf_info(0,6,'NCS2006',2)
        if 'M15]' == productFamily:
            return make_shelf_info(0,15,'NCS2015',2)
        raise ValueError("SHELF")
    #****************************************
    #Not worrying about p-shelf at the moment
    if 'PSHELF' == location:
        productFamily = physicalLocation[-9:]
        # if '-2RU]' == productFamily:
        #     return ['p',2]
        if 'F-MF-6RU]' == productFamily:
            return make_shelf_info(1,14,'14 Slot Passive Unit',0)
        if 'MF10-6RU]' == productFamily:
            return make_shelf_info(1,10,'10 Double Slot Passive Unit',0)
        raise ValueError("PSHELF")
    #****************************************
    return make_shelf_info("Neither",0,'Not line card or controller',0)

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

def build_device_string(deviceName, deviceID, deviceIP, chassis_pairings, chasses, active_chassis_list, passive_chassis_list):
    rstring=''
    rstring+="++++++ Summary for "+deviceName+" ++++++"
    rstring+= "\n\tDevice ID: "+str(deviceID)
    rstring+= "\n\tAddress: "+str(deviceIP)
    if len(chassis_pairings)>1:
        rstring+= "\n\n\tMulti Chassis Rack - "+str(len(chasses))+" Shelves"
    else:
        rstring+= "\n\n\tSingle Chassis Rack"
    if len(active_chassis_list)>0:
        rstring+= "\n\tActive Shelves:"
        for dev in active_chassis_list:
            rstring+= "\n\t"+dev+":"
            tnc_util = (float(chassis_pairings[dev][0])/chassis_pairings[dev][1])*100
            lc_util = (float(chassis_pairings[dev][2])/chassis_pairings[dev][3])*100
            rstring+= "\n\t\tControllers: "+str(chassis_pairings[dev][0])+"/"+str(chassis_pairings[dev][1])+" Slots Populated - "+str(format(tnc_util, '.0f'))+"% Utilization"
            rstring+= "\n\t\tService Cards: "+str(chassis_pairings[dev][2])+"/"+str(chassis_pairings[dev][3])+" Slots Populated - "+str(format(lc_util, '.0f'))+"% Utilization"
    if len(passive_chassis_list)>0:
        rstring+= "\n\tPassive Shelves:"
        for dev in passive_chassis_list:
            rstring+= "\n\t"+dev+":"
            lc_util = (float(chassis_pairings[dev][2])/chassis_pairings[dev][3])*100
            rstring+= "\n\t\tService Cards: "+str(chassis_pairings[dev][2])+"/"+str(chassis_pairings[dev][3])+" Slots Populated - "+str(format(lc_util, '.0f'))+"% Utilization"
    rstring+='\n\n'
    return rstring

def get_NCS2KMOD_dev(auth, host, devID):
    # extension = 'InventoryDetails'
    # filters = ".full=true&summary.deviceType=startsWith(\"Cisco NCS 2\")"
    # response = make_get_req(auth, host, extension, filters)
    
    #extension = 'InventoryDetails/7688694'
    extension = 'InventoryDetails/'+devID
    response = make_get_req(auth, host, extension)

    deviceList = response['queryResponse']['entity']
    rstring = ""

    for device in deviceList:
        summary = device['inventoryDetailsDTO']['summary']
        deviceID = summary['deviceId']
        deviceIP = summary['ipAddress']
        deviceName = summary['deviceName']
        deviceType = summary['deviceType']
        lineCards = {}

        active_chassis_list=[]
        passive_chassis_list=[]
        chassis_pairings = {}
        chassisType = ''

        chasses = []
        slotUsage = 0
        capacity = 0
        modules = device['inventoryDetailsDTO']['modules']

        validChassis = False
        tnc_cap = 0
        chassisType = ''

        for module in modules['module']:
            productName = module["productName"]
            physicalModule = "physicalLocation" in module
            # Module must have a physical location

            if physicalModule:
                physicalLocation = module["physicalLocation"]
                if physicalLocation == "PSHELF-1[PSHELF-MF-6RU]":
                    print json.dumps(module, indent=2)
                shelf_info = determine_shelf_info(physicalLocation)
                shelfType = shelf_info['shelfType']
                controllerCapacity = shelf_info['controllerCapacity']
                chassisType = shelf_info['chassisType']
                validModule = shelfType != "Neither"
                # Module must be a linecard or controller in a shelf

                if validModule:
                    if shelfType == "active":
                        fullChassisName = chassisType+'['+physicalLocation[0:7]+']'       
                    elif shelfType == "passive":
                        fullChassisName = chassisType+'['+physicalLocation[0:8]+']'
                    validChassis = True
                    firstAppearance = not physicalLocation in chasses
                    # Seeing the shelf for the first time

                    if firstAppearance:
                        capacity += shelf_info['capacity']
                        chasses.append(physicalLocation)
                        chassis_pairings[fullChassisName] = [0,controllerCapacity,0,shelf_info['capacity']]
                        if shelfType == "active": #active
                            active_chassis_list.append(fullChassisName)
                        elif shelfType == "passive": #passive
                            passive_chassis_list.append(fullChassisName)
            
            productName=productName.replace('=','')
            if validChassis == True:
                
                if productName in LC:
                    if physicalLocation == "PSHELF-1[PSHELF-MF-6RU]":
                        print productName   
                    #print '********* IN ********'
                    chassis_pairings[fullChassisName][2] += 1
                    if productName in lineCards:
                        lineCards[productName] += 1
                    else:
                        lineCards[productName] = 1

                    if productName in TWORU and chassisType != "10 Double Slot Passive Unit":
                        print deviceIP
                        print productName
                        print chassis_pairings[fullChassisName][2]
                        chassis_pairings[fullChassisName][2] += 1
                if productName in TNC:
                    #print '********* IN ********'
                    chassis_pairings[fullChassisName][0] += 1
                validChassis = False

        rstring += build_device_string(deviceName, deviceID, deviceIP, chassis_pairings, chasses, active_chassis_list, passive_chassis_list)

    return rstring



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
    # deviceList=['7688694']

    output_file = 'inventory_dump_single.txt'
    with open(output_file, "wb") as f:
        for dev in deviceList:
            f.write(get_NCS2KMOD_dev(auth, host_addr, dev))

    # output_file = 'inventory_dump.txt'
    # with open(output_file, "wb") as f:
    #     for dev in deviceList:
    #         f.write(get_NCS2KMOD_dev(auth, host_addr, dev))

        
    

    # ref_out = '2k_update.csv'
    # with open(ref_out, 'w') as output:
    #     fieldnames = ['deviceID', 'deviceIP', 'deviceName', 'deviceType', 'lineCards', 'slotUsage', 'capacity', 'utilization']
    #     out_writer = csv.DictWriter(output, fieldnames=fieldnames)
    #     out_writer.writerow({'deviceID': 'Device ID', 'deviceIP':'Device IP', 'deviceName':'Device Name', 'deviceType':'Device Type', 'lineCards':'Line Cards', 'slotUsage':'Slot Usage', 'capacity':'Capacity', 'utilization':'Utilization'})
    #     for device in deviceList:
    #         out_writer.writerow({'deviceID':device['deviceID'], 'deviceIP':device['deviceIP'], 'deviceName':device['deviceName'],'deviceType':device['deviceType'], 'lineCards':device['lineCards'], 'slotUsage':device['slotUsage'], 'capacity':device['capacity'], 'utilization':device['utilization']})
    # 