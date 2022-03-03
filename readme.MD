## ibmcloud_inv.py
This Dynamic Inventory plugin for Ansible allows the IBM Cloud VPC to be queried to return a current
inventory of instances grouped by various configurable parameters.

<b>ibmcloud_inv.ini</b> file should be created in the same directory.

The <b>[api]</b> section defines the version, region, and generation of VPC to use.  All fields are required.
```
apiversion = 2022-02-22
region = us-south
```

You IBM Cloud apiKey should not be stored in this file, and instead should be stored in the environment variable <b>IC_API_KEY</b><br>
``
export IC_API_KEY=123456789a
``

In the <b>[ibmcloud]</b> section, define the parameters for what instances are included in the inventory and how they are grouped.

<b>ansible_host_variable</b> Determines how the ansible host variable is set.
```
ansible_host_variable = floating_ip (Returns the Floating IP address or Public ip address of the primary interface of the instance.)
ansible_host_variable = private_ip (Return the VPC private IP address of the primary interface of the instance.)
```

By default, only instances in the 'running' state are returned. Set <b>'all_instances = True' </b> to return all instances,
 including instances which are suspended regardless of current state.

The following parameters can be set to either <b>True</b> or <b>False</b> to determine whether they are group together by this type the type.   One
or more can be selected.

```
group_by_region = False
group_by_zone = True
group_by_platform = False
group_by_vpc = True
group_by_security_group = False
group_by_resource_group = False
group_by_tags = True
```
To use with ansible use the `ansible-inventory` or `ansible-playbook` commands referencing the dynamic inventory directory.

``
ansible-inventory -i inventory --list
``
