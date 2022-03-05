## ibmcloud_inv.py
This Dynamic Inventory plugin for Ansible allows the IBM Cloud VPC to be queried to return a current
inventory of instances grouped by configurable parameters such as subnet, security_group or tag.

### V2 Changes
- Inventory queried using IBM Cloud Virtual Private Cloud (VPC) Python SDK Version 0.10.0
- Addition of IBM Cloud VPC Baremetal resource type
- Addition of group by resource type
- Addition of Placement Groups and the ability to group by placement group
- Addition of Dedicated Host field if present
- Addition of GPU fields
- Ability to query all regions; and movement of region parameter to [ibmcloud] seciont of ini file
- Varoious other fixes

### Configuration

<b>ibmcloud_inv.ini</b> file should be created in the same directory.

The <b>[api]</b> section defines region, VPC to use.  If not specified, or configured as "all", all regions will be queried.
```
region = us-south
```

You IBM Cloud apiKey should not be stored in this file, and instead should be stored in the environment variable *IC_API_KEY*

```
export IC_API_KEY=123456789a
```

In the <b>[ibmcloud]</b> section, define the parameters for what instances are included in the inventory and how they are grouped.

<b>ansible_host_variable</b> Determines how the ansible host variable is set.

- ansible_host_variable = **floating_ip** - returns the Public Floating IP address  of the primary interface of the instance.
- ansible_host_variable = **private_ip** - returns the Private VPC IP address of the primary interface of the instance.

By default, only instances in the 'running' state are returned. Set <b>'all_instances = True' </b> to return all instances,
 including instances which are suspended regardless of current state.

The following parameters can be set to either <b>True</b> or <b>False</b> to determine whether they are group together by this type the type.   One
or more can be selected.

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

To use with ansible use the `ansible-inventory` or `ansible-playbook` commands referencing the dynamic inventory directory.

```
ansible-inventory -i inventory --list
```

