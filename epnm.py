"""
WARNING:
This script is meant for educational purposes only.
Any use of these scripts and tools is at
your own risk. There is no guarantee that
they have been through thorough testing in a
comparable environment and we are not
responsible for any damage or data loss
incurred with their use.

INFORMATION:
If you have further questions about this API and script, please contact GVE. Here are the contact details:
   For internal Cisco employees, please contact GVE at http://go2.cisco.com/gve
   For Cisco partners, please open a case at www.cisco.com/go/ph

"""

import requests
import json
import contextlib
import base64
from pprint import pprint

nodePrefix = 'MD=CISCO_EPNM!ND='
nodePrefixLen = 17

class EPNM(object):
    requests.packages.urllib3.disable_warnings()

    def __init__(self, ip, user_auth, verify=False):
        self.ip = ip
        self.verify = verify
        self.url = 'https://' + self.ip + '/restconf/data/v1'
        self.authorization = "Basic " + user_auth

        self.getHeaders = {
            'Authorization': self.authorization,
            'Accept': 'application/json'
        }

        self.postHeaders = {
            'Authorization': self.authorization,
            'cache-control': "no-cache",
            'content-type': "application/json"
        }

    def getAlarmList(self, dev_id='', max_count=99):
        # function returns alarm list device info for devices managed by EPNM at self.ip
        getURL = self.url + '/cisco-rtm:alarm'
        alarmListResponse = {}

        if dev_id != '':
            getURL = getURL + '/' + str(dev_id) + '.json'

        print (getURL)

        last_index = -1
        start_index = 0
        response = {}
        while max_count - last_index > 0 and (last_index + 1) % 100 == 0 :
            getURLLocal = getURL + '?.startIndex=' + str(start_index)
            response = requests.get(getURLLocal, headers=self.getHeaders, verify=self.verify)
            if last_index == -1 :
                alarmListResponse = response.json()['com.response-message']['com.data']['alm.alarm']
                #print(alarmListResponse)
            else :
                alarmListResponse.extend(response.json()['com.response-message']['com.data']['alm.alarm'])
                #print(alarmListResponse)

            last_index = response.json()['com.response-message']['com.header']['com.lastIndex']
            start_index = last_index + 1

        return alarmListResponse

    def getGroupList(self, max_count=''):
        # function returns group definition list for groups defined in EPNM at self.ip
        getURL = self.url + '/cisco-resource-physical:group'

        if max_count != '':
            getURL += '?.maxCount='+max_count
        else:
            getURL = getURL

        response = requests.get(getURL, headers=self.getHeaders, verify=self.verify)

        return response

    def buildEPNMGroupList(self, groupList, containingGroupType, unnassignedGroup):
        # function returns a list of EPNMGroup Objects that contain a list of devices for each group defined in EPNM at self.ip
        groupObjects = []
        for group in groupList['com.response-message']['com.data']['nd.group']:

            if ('nd.node' in group and 'nd.containing-group' in group and group[
                'nd.containing-group'] == containingGroupType and group['nd.fdn'] != unnassignedGroup):
                #print('    contained group:' + group['nd.containing-group'])
                group_name = group['nd.name']
                #print('    group:' + group_name)
                nodeList = []

                for node in group['nd.node']:
                    pos = node.find(nodePrefix)
                    node_name = node[nodePrefixLen:]
                    nodeList.append(node_name)
                    #print('    node: ' + node_name)

                epnmGroup = EPNMGroup(group_name, nodeList)
                groupObjects.append(epnmGroup)

        return groupObjects

class EPNMGroup(object):
    def __init__(self, group_name, nodes, verify=False):
        self.group_name = group_name
        self.nodes = nodes

    def isNodeInGroup(self,node) :
        for gnode in self.nodes :
            if gnode == node :
                return 1