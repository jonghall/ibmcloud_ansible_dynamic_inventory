#!/usr/bin/env python3

# Ansible dynamic inventory for IBM Cloud VPC Infrastructure
# Copyright (c) 2022
#
ti_version = '2.0'
# Based on dynamic inventory for IBM Cloud from steve_strutt@uk.ibm.com
# 06-26-2019 - 1.0 - Modified to use with the IBM VPC Gen 1 / Gen 2
# 06-20-2020 - 1.1 - Added gen2 global tagging support
# 03-03-2022 - 1.2 - Updated libraries Incorporated changes from community & updated api version
# 03-05-2022 - 2.0 - Added Bare Metal, additional Fields, and ability to query multiple regions
#                  - Inventory queried using IBM Cloud Virtual Private Cloud (VPC) Python SDK Version 0.10.0
#                  - Addition of IBM Cloud VPC Baremetal resource type
#                  - Addition of group by resource type
#                  - Addition of Placement Groups and the ability to group by placement group
#                  - Addition of Dedicated Host field if present
#                  - Addition of GPU fields
#                  - Ability to query all regions by default or specify specific regions
#                  - Removal of [api] section which is not needed by the SDK
#                  - Movement of optional region variable to the [ibmcloud] section
#                  - Various other fixes
#
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
# IBM Cloud apiKey should be stored in env variable IC_API_KEY
#
# Successful execution returns groups with lists of hosts and _meta/hostvars with a detailed
# host listing.
#
# Validate successful operation with ansible:
#   With - 'ansible-inventory -i inventory --list'
#          'ansible-playbook - i inventory playbook.yaml

######################################################################

import json, configparser, os, sys, requests, urllib
from distutils.util import strtobool
from collections import defaultdict
from argparse import ArgumentParser
from ansible.module_utils._text import to_text
from ibm_vpc import VpcV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import ApiException
from ibm_platform_services import GlobalTaggingV1

def parse_params():
    parser = ArgumentParser('IBM Cloud Dynamic Inventory')
    parser.add_argument('--list', action='store_true', default=True, help='List IBM Cloud hosts in specified VPC')
    parser.add_argument('--inifile', '-i', action='store', dest='inifile', help='inifile which contains the APIKey required parameters')
    parser.add_argument('--version', '-v', action='store_true', help='Show version')
    args = parser.parse_args()

    if not args.inifile:
        dirpath = os.path.dirname(os.path.realpath(sys.argv[0]))
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

        if 'group_by_region' in config["ibmcloud"]:
            args.group_by_region = strtobool(config["ibmcloud"]["group_by_region"])
        else:
            args.group_by_region = False

        if 'group_by_region' in config["ibmcloud"]:
            args.group_by_zone = strtobool(config["ibmcloud"]["group_by_zone"])
        else:
            args.group_by_zone = False

        if 'group_by_image' in config["ibmcloud"]:
            args.group_by_image = strtobool(config["ibmcloud"]["group_by_image"])
        else:
            args.group_by_image = False

        if 'group_by_profile' in config["ibmcloud"]:
            args.group_by_profile = strtobool(config["ibmcloud"]["group_by_profile"])
        else:
            args.group_by_profile = False

        if 'group_by_vpc' in config["ibmcloud"]:
            args.group_by_vpc = strtobool(config["ibmcloud"]["group_by_vpc"])
        else:
            args.group_by_vpc = False

        if 'group_by_security_group' in config["ibmcloud"]:
            args.group_by_security_group = strtobool(config["ibmcloud"]["group_by_security_group"])
        else:
            args.group_by_security_group = False

        if 'group_by_resource_group' in config["ibmcloud"]:
            args.group_by_resource_group = strtobool(config["ibmcloud"]["group_by_resource_group"])
        else:
            args.group_by_resource_group = False

        if 'group_by_resource_type' in config["ibmcloud"]:
            args.group_by_resource_type = strtobool(config["ibmcloud"]["group_by_resource_type"])
        else:
            args.group_by_resource_type = False

        if 'group_by_placement_target' in config["ibmcloud"]:
            args.group_by_placement_target = strtobool(config["ibmcloud"]["group_by_placement_target"])
        else:
            args.group_by_placement_target = False

        if 'group_by_tags' in config["ibmcloud"]:
            args.group_by_tags = strtobool(config["ibmcloud"]["group_by_tags"])
        else:
            args.group_by_tages = False

        if 'all_instances' in config["ibmcloud"]:
            args.all_instances = strtobool(config['ibmcloud']['all_instances'])
        else:
            args.all_instance = False

        if 'ansible_host_variable' in config["ibmcloud"]:
            args.ansible_host_variable = config['ibmcloud']['ansible_host_variable']
        else:
            args.ansible_host_vraiable = "private_ip_address"

        if 'region' in config["ibmcloud"]:
            args.region = config['ibmcloud']['region']
        else:
            args.region = "all"

    return args

def gettags(instancecrn):
    ################################################
    ## Retreive and Parse Tagging for Instance
    ################################################

    try:
        tags = taggingservice.list_tags(attached_to=instancecrn).get_result()
    except ApiException as e:
        print("Get tags failed with status code " + str(e.code) + ": " + e.message)
        quit()

    taglist = []
    for tag in tags["items"]:
        taglist.append(tag["name"])
    return taglist

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

        if self.args.region == "all":
            try:
                regions = vpcservice.list_regions().get_result()
            except ApiException as e:
                print("List regions failed with status code " + str(e.code) + ": " + e.message)
                quit()
        else:
            try:
                region = vpcservice.get_region(name=self.args.region).get_result()
            except ApiException as e:
                print("Get region failed with status code " + str(e.code) + ": " + e.message)
                quit()
            regions = {"regions": [region]}

        for region in regions["regions"]:
        # Change to regional endpoint
            vpcservice.set_service_url(region["endpoint"]+"/v1")

            for name, attributes, groups in self.get_instances():
                ibmcloud_hosts.append(name)
                hosts_vars[name] = attributes
                for group in list(groups):
                    group_hosts[group].append(name)

            for name, attributes, groups in self.get_baremetal():
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

        try:
            instances = vpcservice.list_instances().get_result()['instances']
        except ApiException as e:
            print("Get instances failed with status code " + str(e.code) + ": " + e.message)
            quit()

        for instance in instances:
            if instance["status"] == "running" or self.args.all_instances:
                name = instance['name']
                try:
                    primary_network_interface = vpcservice.get_instance_network_interface(instance_id=instance["id"],
                                                        id=instance["primary_network_interface"]["id"]).get_result()
                except ApiException as e:
                    print("Get primary_network_interface failed, status code " + str(e.code) + ": " + e.message)
                    quit()

                resource_group = instance["resource_group"]
                attributes = {
                    'href': instance["href"],
                    'id': instance["id"],
                    'created_at': instance["created_at"],
                    'image': instance["image"]["name"],
                    'memory': instance["memory"],
                    'vcpu': instance["vcpu"],
                    'region': self.args.region,
                    'vpc': instance["vpc"]["name"],
                    'zone': instance["zone"]["name"],
                    'status': instance["status"],
                    'profile': instance["profile"]["name"],
                    'resource_type': instance["resource_type"],
                    'resource_group_id': resource_group['id'],
                    'resource_group': resource_group["name"],
                    'primary_ipv4_address': primary_network_interface["primary_ipv4_address"],
                    'subnet': primary_network_interface["subnet"]["name"],
                    'subnet_id': primary_network_interface["subnet"]["id"],
                    'security_group': primary_network_interface["security_groups"][0]["name"],
                    'security_group_id': primary_network_interface["security_groups"][0]["id"],
                    'ansible_ssh_user': 'root',
                    'tags': gettags(instance["crn"])
                }

                if 'metadata_service' in instance:
                    attributes['metadata_service'] = instance["metadata_service"]["enabled"]

                if 'dedicated_host' in instance:
                    attributes['dedicated_host_name'] = instance['dedicated_host']['name']

                if "placement_target" in instance:
                    attributes["placement_target"] = instance["placement_target"]["name"]

                if 'gpu' in instance:
                    attributes['gpu_count'] = instance['gpu']

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

                if self.args.group_by_image:
                    group.append(attributes["image"].translate({ord(c): '_' for c in ' .-/'}))

                if self.args.group_by_profile:
                    group.append(attributes["profile"].translate({ord(c): '_' for c in ' .-/'}))

                if self.args.group_by_security_group:
                    group.append(attributes["security_group"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_placement_target:
                    if 'placement_target' in attributes:
                        group.append(attributes["placement_target"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_vpc:
                    group.append(attributes["vpc"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_resource_group:
                    group.append(attributes['resource_group'].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_resource_type:
                    group.append(attributes["resource_type"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_tags:
                    for tag in attributes["tags"]:
                        group.append(tag.translate({ord(c): '_' for c in '-'}))


                yield name, attributes, group

    def get_baremetal(self):

        try:
            baremetalservers= vpcservice.list_bare_metal_servers().get_result()['bare_metal_servers']
        except ApiException as e:
            print("Get baremetal servers failed with status code " + str(e.code) + ": " + e.message)
            quit()

        for bm in baremetalservers:
            if bm["status"] == "running" or self.args.all_instances:
                name = bm['name']
                try:
                    primary_network_interface = vpcservice.get_bare_metal_server_network_interface(bare_metal_server_id=bm["id"],
                                                                id=bm["primary_network_interface"]["id"]).get_result()
                except ApiException as e:
                    print("Get bm_primary_network_interface failed, status code " + str(e.code) + ": " + e.message)
                    quit()

                resource_group = bm["resource_group"]
                attributes = {
                    'href': bm["href"],
                    'id': bm["id"],
                    'created_at': bm["created_at"],
                    'memory': bm["memory"],
                    'cpu': bm['cpu'],
                    'region': self.args.region,
                    'vpc': bm["vpc"]["name"],
                    'zone': bm["zone"]["name"],
                    'status': bm["status"],
                    'profile': bm["profile"]["name"],
                    'resource_type': bm["resource_type"],
                    'resource_group_id': resource_group['id'],
                    'resource_group': resource_group["name"],
                    'primary_ipv4_address': primary_network_interface["primary_ipv4_address"],
                    'subnet': primary_network_interface["subnet"]["name"],
                    'subnet_id': primary_network_interface["subnet"]["id"],
                    'security_group': primary_network_interface["security_groups"][0]["name"],
                    'security_group_id': primary_network_interface["security_groups"][0]["id"],
                    'ansible_ssh_user': 'root',
                    'tags': gettags(bm["crn"])
                }

                if "enable_secure_boot" in bm:
                    attributes["enable_secure_boot"] = bm['enable_secure_boot']

                if "trusted_platform_module" in bm:
                    attributes["trusted_platform_module"] = bm['trusted_platform_module']

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

                if self.args.group_by_security_group:
                    group.append(attributes["security_group"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_vpc:
                    group.append(attributes["vpc"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_profile:
                    group.append(attributes["profile"].translate({ord(c): '_' for c in ' .-/'}))

                if self.args.group_by_resource_group:
                    group.append(attributes['resource_group'].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_resource_type:
                    group.append(attributes["resource_type"].translate({ord(c): '_' for c in '-'}))

                if self.args.group_by_tags:
                    for tag in attributes["tags"]:
                        group.append(tag.translate({ord(c): '_' for c in '-'}))

                yield name, attributes, group

if __name__ == '__main__':
    authenticator = IAMAuthenticator(os.environ.get("IC_API_KEY"))
    vpcservice = VpcV1(authenticator=authenticator)
    taggingservice = GlobalTaggingV1(authenticator=authenticator)
    IBMCloudInventory()
