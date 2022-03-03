#!/usr/bin/env python3

# Ansible dynamic inventory for IBM Cloud VPC Infrastructure
# Copyright (c) 2020
#
ti_version = '0.8'
# Based on dynamic inventory for IBM Cloud from steve_strutt@uk.ibm.com
# 06-26-2019 - 1.0 - Modified to use with the IBM VPC Gen 1 / Gen 2
#                    & RIAS API verison=2019-06-04
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Can be used alongside static inventory files in the same directory 
#
# ibmcloud_inv.ini file in the same directory as this script contains
# [ibmcloud] section which lets you set serveral parameters on how groups
# are created and hosts fileterd.
#
# The [api] section defines api version region to use
#
# IBM Cloud apiKey should be stored in env variable IC_API_KEY
#
# Successful execution returns groups with lists of hosts and _meta/hostvars with a detailed
# host listing.
#
# Validate successful operation with ansible:
#   With - 'ansible-inventory -i inventory --list'
#

######################################################################

import json, configparser, os, sys, requests, urllib
from distutils.util import strtobool
from collections import defaultdict
from argparse import ArgumentParser
from ansible.module_utils._text import to_text

def parse_params():
    parser = ArgumentParser('IBM Cloud Dynamic Inventory')
    parser.add_argument('--list', action='store_true', default=True, help='List IBM Cloud hosts in specified VPC')
    parser.add_argument('--inifile', '-i', action='store', dest='inifile', help='inifile which contains the APIKey required parameters')
    parser.add_argument('--version', '-v', action='store_true', help='Show version')
    args = parser.parse_args()

    if not args.inifile:
        dirpath = os.path.dirname(os.path.realpath(sys.argv[0]))
        print()
        config = configparser.ConfigParser()
        ini_file = 'ibmcloud_inv.ini'
        try:
            # attempt to open ini file first. Only proceed if found
            # assume execution from the ansible playbook directory
            filepath = dirpath + '/' + ini_file
            open(filepath)

        except FileNotFoundError:
            raise Exception("Unable to find or open specified ini file")
        else:
            config.read(filepath)

        config.read(filepath)

        args.group_by_region = strtobool(config["ibmcloud"]["group_by_region"])
        args.group_by_zone = strtobool(config["ibmcloud"]["group_by_zone"])
        args.group_by_platform = strtobool(config["ibmcloud"]["group_by_platform"])
        args.group_by_vpc = strtobool(config["ibmcloud"]["group_by_vpc"])
        args.group_by_security_group = strtobool(config["ibmcloud"]["group_by_security_group"])
        args.group_by_resource_group = strtobool(config["ibmcloud"]["group_by_resource_group"])
        args.group_by_tags = strtobool(config["ibmcloud"]["group_by_tags"])
        args.all_instances = strtobool(config['ibmcloud']['all_instances'])
        args.ansible_host_variable = config['ibmcloud']['ansible_host_variable']

        #args.iamtoken = getiamtoken(config['api']['apikey'])
        args.iamtoken = getiamtoken(os.environ.get("IC_API_KEY"))
        args.apiversion = "?version=" + config["api"]["apiversion"] + "&generation=" + config["api"]["generation"]
        args.generation = config['api']['generation']
        args.region = config['api']['region']
        region = apigetregion(args)

        if region["status"] == 'available':
                args.iaas_endpoint = region["endpoint"]
        else:
            print ("Region not available or invalid.")
            quit()

    return args

def getiamtoken(apikey):
    ################################################
    ## Lookup interface by ID
    ################################################

    headers = {"Content-Type": "application/x-www-form-urlencoded",
               "Accept": "application/json"}

    parms = {"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": apikey}

    try:
        resp = requests.post("https://iam.cloud.ibm.com/identity/token?"+urllib.parse.urlencode(parms), headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
        quit()
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
        quit()
    except requests.exceptions.HTTPError as errb:
            print("Invalid token request.")
            print("template=%s" % parms)
            print("Error Data:  %s" % errb)
            print("Other Data:  %s" % resp.text)
            quit()


    iam = resp.json()

    iamtoken = {"Authorization": "Bearer " + iam["access_token"]}

    return iamtoken

def apigetregion(args):
    #############################
    # Get Region
    #############################
    region = None

    try:
        uri = 'https://us-south.iaas.cloud.ibm.com/v1/regions/'+args.region+args.apiversion
        resp = requests.get(uri, headers=args.iamtoken, timeout=30)
        resp.raise_for_status()

    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
        quit()
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
        quit()
    except requests.exceptions.HTTPError as errb:
        print("Unknown Error:", errb)
        print(resp.error)
        quit()

    if resp.status_code == 200:
        region = json.loads(resp.content)
    return region

def apigetinterface(args, href):
    ################################################
    ## Lookup interface by href
    ################################################

    try:
        resp = requests.get(href + args.apiversion, headers=args.iamtoken, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
        quit()
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
        quit()
    except requests.exceptions.HTTPError as errb:
        print("Unknown Error:", errb)
        print(resp.error)
        quit()

    if resp.status_code == 200:
        interface = json.loads(resp.content)

    return interface

def apigetresourcegroup(args, href):
    ################################################
    ## Lookup resourcegroup by href
    ################################################

    try:
        resp = requests.get(href + args.apiversion, headers=args.iamtoken, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
        quit()
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
        quit()
    except requests.exceptions.HTTPError as errb:
        print("Unknown Error:", errb)
        print(resp.error)
        quit()

    if resp.status_code == 200:
        resourcegroup = json.loads(resp.content)

    return resourcegroup

def apigettags(args, instancecrn):
    ################################################
    ## Get Instance Tag
    ################################################
    tags = []
    start = 0
    limit = 100
    url = "https://tags.global-search-tagging.cloud.ibm.com/v3/tags?attached_to="+instancecrn+"&limit=" + str(limit)
    while True:
        try:
            resp = requests.get(url, headers=args.iamtoken, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as errc:
            print("Error Connecting:", errc)
            quit()
        except requests.exceptions.Timeout as errt:
            print("Timeout Error:", errt)
            quit()
        except requests.exceptions.HTTPError as errb:
            unknownapierror(resp)

        if resp.status_code == 200:
            result = json.loads(resp.content)
            #total_count = result["total_count"]
            tags = tags + result["items"]
            if "next" in result:
                url=result["next"]["href"]
                continue
            else:
                break
    taglist = []
    for tag in tags:
        taglist.append(tag["name"])
    return taglist

def apigetinstances(args):
    ################################################
    ## Get Instances
    ################################################

    instances = []
    start = 0
    limit = 100
    url = args.iaas_endpoint + '/v1/instances/' + args.apiversion + "&limit=" + str(limit)

    while True:
        try:
            resp = requests.get(url, headers=args.iamtoken, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as errc:
            print("Error Connecting:", errc)
            quit()
        except requests.exceptions.Timeout as errt:
            print("Timeout Error:", errt)
            quit()
        except requests.exceptions.HTTPError as errb:
            unknownapierror(resp)

        if resp.status_code == 200:
            result = json.loads(resp.content)
            #total_count = result["total_count"]
            instances = instances + result["instances"]
            if "next" in result:
                url=result["next"]["href"]
                continue
            else:
                break
    return instances

class IBMCloudInventory():

    def __init__(self):
        self.args = parse_params()
        if self.args.version:
            print(ti_version)
        elif self.args.list:
            print(self.list_all())

    def list_all(self):
        ibmcloud_hosts = []
        vars = {}
        hosts_vars = {}
        attributes = {}
        groups = {}
        groups_json = {}
        inv_output = {}
        group_hosts = defaultdict(list)

        for name, attributes, groups in self.get_instances():
            ibmcloud_hosts.append(name)
            hosts_vars[name] = attributes
            for group in list(groups):
                group_hosts[group].append(name)

        inv_output["All"] = {
            "hosts": ibmcloud_hosts,
        }

        inv_output["_meta"] = {'hostvars': hosts_vars}

        for group in group_hosts:
            inv_output[group] = {'hosts': group_hosts[group]}

        return to_text(json.dumps(inv_output, indent=2))

    def get_instances(self):

        instances = apigetinstances(self.args)

        for instance in instances:
            if instance["status"] == "running" or self.args.all_instances:
                name = instance['name']
                primary_network_interface = apigetinterface(self.args, instance["primary_network_interface"]["href"])
                resource_group = apigetresourcegroup(self.args, instance["resource_group"]["href"])
                attributes = {
                    'href': instance["href"],
                    'id': instance["id"],
                    'created_at': instance["created_at"],
                    'image': instance["image"]["name"],
                    'memory': instance["memory"],
                    'region': self.args.region,
                    'vpc': instance["vpc"]["name"],
                    'zone': instance["zone"]["name"],
                    'status': instance["status"],
                    'profile': instance["name"],
                    'resource_group_id': resource_group['id'],
                    'resource_group': resource_group["name"],
                    'primary_ipv4_address': primary_network_interface["primary_ipv4_address"],
                    'subnet': primary_network_interface["subnet"]["name"],
                    'subnet_id': primary_network_interface["subnet"]["id"],
                    'security_group': primary_network_interface["security_groups"][0]["name"],
                    'security_group_id': primary_network_interface["security_groups"][0]["id"],
                    'ansible_ssh_user': 'root',
                    'tags': apigettags(self.args, instance["crn"])
                }

                if 'cpu' in instance:
                    attributes['cpu'] = instance["cpu"]
                else:
                    attributes['cpu'] = instance["vcpu"]

                if "floating_ips" in primary_network_interface:
                    attributes["floating_ip"] = primary_network_interface["floating_ips"][0]["address"]

                if self.args.ansible_host_variable == "private_ip":
                    attributes['ansible_host'] = primary_network_interface["primary_ipv4_address"]
                elif self.args.ansible_host_variable == "floating_ip" and "floating_ips" in primary_network_interface:
                    attributes['ansible_host'] = primary_network_interface["floating_ips"][0]["address"]

                group = []

                if self.args.group_by_region:
                    group.append(attributes["region"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_zone:
                    group.append(attributes["zone"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_platform:
                    group.append(attributes["image"].translate({ord(c): '_' for c in ' .-/'}))

                if self.args.group_by_security_group:
                    group.append(attributes["security_group"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_vpc:
                    group.append(attributes["vpc"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_resource_group:
                    group.append(attributes['resource_group'].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_tags:
                    for tag in attributes["tags"]:
                        group.append(tag.translate({ord(c): '_' for c in '-'}))

                yield name, attributes, group

if __name__ == '__main__':

    IBMCloudInventory()
