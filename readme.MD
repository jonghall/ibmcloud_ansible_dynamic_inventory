## ibmcloud_inv.py
This Dynamic Inventory plugin for Ansible allows IBM Cloud VPC to be queried to return a current
inventory of hosts grouped by configurable parameters such as subnet, security_group or tag.

### V2 Changes
- Inventory queried using IBM Cloud Virtual Private Cloud (VPC) Python SDK Version 0.10.0
- Addition of IBM Cloud VPC Baremetal resource type
- Addition of group by resource type
- Addition of Placement Groups and the ability to group by placement group
- Addition of Dedicated Host field if present
- Addition of GPU fields
- Ability to query all regions by default or specify specific regions
- Removal of [api] section which is not needed by the SDK
- Movement of optional region variable to the [ibmcloud] section
- Varoious other fixes

### Configuration

<b>ibmcloud_inv.ini</b> file should be created in the same directory as ibmcloud_inv.py.

Your IBM Cloud apiKey should not be stored in this file, and instead should be specified as an environment variable.

```
export IC_API_KEY=<ibmcloud apikey>
```

In the <b>[ibmcloud]</b> section of the ibmcloud_inv.ini file defines the parameters that determine which hosts are
included in the inventory and how they are grouped for usage as roles within a playbook.

<b>ansible_host_variable</b> Determines how the ansible host variable is set.
- **floating_ip** - returns the Public Floating IP address  of the primary interface of the instance.
- **private_ip** - returns the Private IP address of the primary interface of the instance.
```
ansible_host_varaible = private_ip
```

By default, only instances in the 'running' state are returned. Set <b>'all_instances = True' </b> to return all instances,
 including instances which are stopped or in a non running state.
```
all_instances = True
```

By default all regions will be queried.   If region is specified the query will be limited to the specified region.
```
region = us-south
```

The following parameters can be set to either <b>True</b> or <b>False</b> to determine whether they are group together
for type specified.  One or more can be choosen.

```
group_by_region = False
group_by_zone = True
group_by_image = False
group_by_vpc = True
group_by_security_group = False
group_by_resource_group = False
group_by_tags = True
group_by_resource_type = True
group_by_placement_target = True
```

### Usage
To use with ansible use the `ansible-inventory` or `ansible-playbook` commands referencing the dynamic inventory directory.
```
ansible-inventory -i inventory --list
ansible-playbook -i inventory playbook.yaml
```

