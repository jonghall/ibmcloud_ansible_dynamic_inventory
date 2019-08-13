## ibmcloud_inv.py
This Dynamic Inventory plugin for Ansible allows the IBM Cloud VPC Classic and VPC API to be queried to return a current
inventory of instances grouped by various configurable parameters.

<b>ibmcloud_inv.ini</b> file should be created in the same directory.

The <b>[api]</b> section defines the apikey, version, region, and generation of VPC to use.  All fields are required.

```
apikey = apikey
apiversion = 2019-06-04
region = us-south
generation = 2
```


In the <b>[ibmcloud]</b> defines parameters on what instances are included in the inventory and how they are grouped.

<b>ansible_host_variable</b> Determines how the ansible host variable is set.
```
ansible_host_variable = floating_ip (Returns the IP address as the public floating ip address.)
ansible_host_variable = private_ip (Return the VPC private IP address of the primary interface.)
```

By default, only instances in the 'running' state are returned. Set <b>'all_instances = True' </b> to return all instances,
 including instances which are suspended regardless of current state.

The following parameters can be set to <b> True </b> to determine whether the creation of a group by the type occurs.   One
or more can be selected.

```
group_by_region = True
group_by_zone = True
group_by_platform = True
group_by_vpc = True
group_by_security_group = True
group_by_resource_group = True
```


