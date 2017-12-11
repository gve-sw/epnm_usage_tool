#!/usr/bin/env python
__author__ = "Michael Castellana and Steven Yee"
__email__ = "micastel@cisco.com and steveyee@cisco.com"
__status__ = "Development"

#import necessary libraries
import base64, getpass, requests, json, sys, smtplib, csv, os
from .. import opensesame
from email.mime.multipart import MIMEMultipart
from email.message import Message
from email.mime.text import MIMEText
from email import encoders
from email.mime.base import MIMEBase

class EPNM_Usage:

    requests.packages.urllib3.disable_warnings()

    def __init__(self,host, user, pwd, SLOTS=[], TNC=[], LC=[], TWORU=[], verify=False):
        self.authorization = "Basic " + base64.b64encode(user + ":" + pwd)
        self.host = host
        self.SLOTS=SLOTS
        self.TNC=TNC
        self.LC=LC
        self.TWORU=TWORU


    def get_headers(self, auth, content_type = "application", cache_control = "no-cache"):
        headers={
            'content-type': content_type,
            'authorization': self.authorization,
            'cache-control': cache_control,
        }
        return headers

    def get_response(self, url, headers, requestType = "GET", verify = False):
        return requests.request(requestType, url, headers=headers, verify = verify).json()

    def make_get_req(self, auth, host, ext, filters = ""):
        headers = self.get_headers(auth)
        url = "https://"+host+"/webacs/api/v1/data/"+ext+".json?"+filters
        return self.get_response(url, headers, requestType = "GET", verify = False)

    def make_group_get_req(self, auth, host, ext, filters = ""):
        headers = self.get_headers(auth)
        url = "https://"+host+"/webacs/api/v1/op/groups/"+ext+".json?"+filters
        return self.get_response(url, headers, requestType = "GET", verify = False)

    def get_device_ID_list(self, response):
        id_list = []
        for item in response:
            id_list.append(str(item['$']))
        return id_list

    def send_email(self, destination_address, source_address, subject, attachment_url):
        email_message = MIMEMultipart()
        email_message['subject'] = subject
        email_message['From'] = source_address
        email_message['To'] = destination_address
        message_body = MIMEText("Attached is EPNM Usage report.")
        email_message.attach(message_body)
        with open(attachment_url) as file:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(file.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment',
                              filename=os.path.basename(attachment_url))
        email_message.attach(attachment)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(source_address, opensesame.password)
        server.sendmail(source_address, destination_address, email_message.as_string())
        server.quit()


    def make_shelf_info(self,shelfTypeRaw, capacity, chassisType, controllerCapacity):
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

    def make_r_dict(self, devName, devID, devIP, active_list, passive_list):
        return {
            'devName' : devName,
            'devID' : devID,
            'devIP' : devIP,
            'active' : active_list,
            'passive' : passive_list

        }
    

    def determine_shelf_info(self,physicalLocation, productName, deviceType):
        if physicalLocation == 'SHELF':
            if '-M2' in productName:
                return self.make_shelf_info(0,2,'NCS2002',1)
            elif '-M6' in productName:
                return self.make_shelf_info(0,6,'NCS2006',2)
            else:
                if '06' == deviceType[-2:]:
                    return self.make_shelf_info(0,6,'NCS2006',2)
                elif '02' == deviceType[-2:]:
                    return self.make_shelf_info(0,2,'NCS2002',1)

        location = physicalLocation[0:6] #0==active, 1==passive
        if 'SHELF-' == location:
            productFamily = physicalLocation[-4:]
            if '-M2]' == productFamily:
                return self.make_shelf_info(0,2,'NCS2002',1)
            if '-M6]' == productFamily:
                return self.make_shelf_info(0,6,'NCS2006',2)
            if 'M15]' == productFamily:
                return self.make_shelf_info(0,15,'NCS2015',2)
            raise ValueError("SHELF")
        #****************************************
        #Not worrying about p-shelf at the moment
        if 'PSHELF' == location:
            productFamily = physicalLocation[-9:]
            # if '-2RU]' == productFamily:
            #     return ['p',2]
            if 'F-MF-6RU]' == productFamily:
                return self.make_shelf_info(1,14,'14 Slot Passive Unit',0)
            if 'MF10-6RU]' == productFamily:
                return self.make_shelf_info(1,10,'10 Double Slot Passive Unit',0)
            raise ValueError("PSHELF")
        #****************************************
        return self.make_shelf_info("Neither",0,'Not line card or controller',0)

    def create_device_model(self,deviceID, deviceIP, deviceName, deviceType, lineCards, slotUsage, capacity, utilization):
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


    def get_group_devs(self, group):
        id_list = []
        #print group
        extension = 'Devices'
        filters = ".full=true&.group="+group+"&deviceType=startsWith(\"Cisco NCS 2\")"
        response = self.make_get_req(self.authorization, self.host, extension, filters)
        # print json.dumps(response, indent=2)
        try:
            response = self.make_get_req(self.authorization, self.host, extension, filters)['queryResponse']['entity']
            for dev in response:
                id_list.append(dev['devicesDTO']['@id'])
            return id_list
        except:
            return id_list

    def get_groupings(self):
        group_list = []
        extension = 'deviceGroups'
        filters = '.full=true'
        response = self.make_get_req(self.authorization, self.host, extension)['mgmtResponse']['grpDTO']
        for item in response:
            group_list.append(item['groupName'])
        return group_list





    def get_ncs2kmod_dev(self, devID):
        # extension = 'InventoryDetails'
        # filters = ".full=true&summary.deviceType=startsWith(\"Cisco NCS 2\")"
        # response = make_get_req(auth, host, extension, filters)
        
        #extension = 'InventoryDetails/7688694'
        extension = 'InventoryDetails/'+devID
        response = self.make_get_req(self.authorization, self.host, extension)

        deviceList = response['queryResponse']['entity']
        rstring = ""
        dev_dict={}
        active={}
        passive={}

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
                    
                    
                    shelf_info = self.determine_shelf_info(physicalLocation, productName, deviceType)
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
                    if productName in self.LC:
                        # if physicalLocation == "PSHELF-1[PSHELF-MF-6RU]":
                        #     print productName   
                        #print '********* IN ********'
                        chassis_pairings[fullChassisName][2] += 1
                        if productName in lineCards:
                            lineCards[productName] += 1
                        else:
                            lineCards[productName] = 1

                        if productName in self.TWORU and chassisType != "10 Double Slot Passive Unit":
                            # print deviceIP
                            # print productName
                            # print chassis_pairings[fullChassisName][2]
                            chassis_pairings[fullChassisName][2] += 1
                    if productName in self.TNC:
                        #print '********* IN ********'
                        chassis_pairings[fullChassisName][0] += 1
                    validChassis = False

            for act in active_chassis_list:
                active[act]=chassis_pairings[act]

            for pasv in passive_chassis_list:
                passive[pasv]=chassis_pairings[pasv]

            rval=self.make_r_dict(deviceName, deviceID, deviceIP, active, passive)

            rstring += self.build_device_string(deviceName, deviceID, deviceIP, chassis_pairings, chasses, active_chassis_list, passive_chassis_list)
        return [rval,rstring]




    def build_device_string(self, deviceName, deviceID, deviceIP, chassis_pairings, chasses, active_chassis_list, passive_chassis_list):
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









    def get_alarms(self, dev):
        extension = 'Alarms'
        filters = '.full=true'
        no_cleared_filters = ".full=true&source=\""+dev+"\"&severity=ne(\"CLEARED\")"
        #***-->group filtering--> .group="GROUP"
        response = self.make_get_req(self.authorization, self.host, extension, no_cleared_filters)['queryResponse']['entity']
        #print len(response)
        r_dict={}
        for item in response:
            info={}
            info['Severity'] = item['alarmsDTO']['severity']
            info['Description'] = item['alarmsDTO']['message']
            info['TimeStamp'] = item['alarmsDTO']['timeStamp']
            info['FailureSource'] = item['alarmsDTO']['source']
            info['LastUpdatedAt'] = item['alarmsDTO']['lastUpdatedAt']
            info['AcknowledgmentStatus'] = item['alarmsDTO']['acknowledgementStatus']
            if 'annotations' in item['alarmsDTO']:
                info['Notes'] = item['alarmsDTO']['annotations']
            else:
                info['Notes'] = "No Notes"
            r_dict[item['alarmsDTO']['@id']] = info
        #     try:
        #         print r_dict['447006516']
        #     except:
        #         pass
        # for k in r_dict:
        #     v=r_dict[k]
        #     print k,v
        return r_dict
        # print json.dumps(response, indent=2)



    def get_locations(self):
        """ Queries all registered Guests"""
        site_list = []
        extension = 'sites'
        filters = '.full=true'
        response = self.make_group_get_req(self.authorization, self.host, extension, filters)['mgmtResponse']['siteOpDTO']
        for item in response:
            if item['deviceCount'] != 0:
                #print item['name'] + ' - '+ str(item['deviceCount'])
                site_list.append(item['name'][item['name'].rfind('/')+1:])

        return site_list
        #print json.dumps(response, indent=2)




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

       