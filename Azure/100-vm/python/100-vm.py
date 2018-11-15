"""Create and manage virtual machines.
This script expects that the following environment vars are set:
AZURE_TENANT_ID: your Azure Active Directory tenant id or domain
AZURE_CLIENT_ID: your Azure Active Directory Application Client ID
AZURE_CLIENT_SECRET: your Azure Active Directory Application Secret
AZURE_SUBSCRIPTION_ID: your Azure Subscription Id
"""

import os.path
import json
import argparse
import sys
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.authorization import AuthorizationManagementClient
import uuid

# This python script was developed by Jianhua WU (wujianhua@outlook.jp) for the
# provisioing of Azure VM on a fresh Azure Subscription.
parser = argparse.ArgumentParser(
    description='parse option arguments passed to this script',
    epilog='Author Jianhua WU',
    prefix_chars='-'
    )
    
parser.add_argument('--DnsZone', nargs='?', default = 'openclouddevops.org', const = 'openclouddevops.org', choices=['openclouddevops.org'], help="your Azure DNS Zone which you intend to register your VM's DNS record")
parser.add_argument('--RgName', required = True, help='your desired Azure Resource Group Name') # the azure resource group for deployment e.g. cystine-ckm-dev-uscentral
parser.add_argument('--VmSize', nargs='?', default = 'Standard_DS2_v2', const = 'Standard_DS2_v2', help='specify the Size of your Azure VM')
parser.add_argument('--DnsPrefixName', required = True, help='specify a DNS prefix name for your VM') #e.g. ckm.ocs.dev.usc
parser.add_argument('--NetworkPrefix', required = True, help='specify the first two octets of your vNet pool address') #e.g. ckm.ocs.dev.usc
parser.add_argument('--Location', nargs='?', default = 'southeastasia', const = 'southeastasia', help='specify Azure location for resource deployment')

parsed_argu = parser.parse_args(sys.argv[1:])

wujianhua_subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
wujianhua_dns_zone = parsed_argu.DnsZone
wujianhua_resource_group = parsed_argu.RgName
#wujianhua_dns_zone_resource_group = parsed_argu.RgDnsZone
wujianhua_vmSize = parsed_argu.VmSize
wujianhua_dns_prefix = parsed_argu.DnsPrefixName
wujianhua_network_prefix = parsed_argu.NetworkPrefix
wujianhua_location = parsed_argu.Location

# Create Azure Service Principal Crendential for the Authentication of Automation Code Below
AzureServicePrincipalcredentials = ServicePrincipalCredentials(
    client_id=os.environ['AZURE_CLIENT_ID'],
    secret=os.environ['AZURE_CLIENT_SECRET'],
    tenant=os.environ['AZURE_TENANT_ID']
)

# Create Azure Resource Management Client handler for Resource Provisioin
client = ResourceManagementClient(AzureServicePrincipalcredentials, wujianhua_subscription_id)


msg = "\nInitializing the provisioning of Azure VM with subscription id: {}, resource group: {}" \
    "\nand public key located at: {}...\n\n"
print(msg.format(wujianhua_subscription_id, wujianhua_resource_group, wujianhua_location))


# Azure uses Resoruce Group for cloud resource organization. Everything which is
# going to be provisioined by this script would be located in the resource group
# wujianhua_resource_group at the location wujianhua_location.
# The value of the variables wujianhua_resource_group and wujianhua_location comes from the argParse above

def wujianhua_rg(resource_group='openCloudDevOps', location='southeastasia'):
    print("Beginning the provisioing of the resource group - {}\n\n".format(resource_group))
    client.resource_groups.create_or_update(
        resource_group,
        {
            'location': location
        }
    )
    print("the resource group - {} has been provisioned successfully\n\n".format(resource_group))


def wujianhua_vNet(AzureServicePrincipalcredentials=AzureServicePrincipalcredentials, subscription_id=wujianhua_subscription_id, resource_group=wujianhua_resource_group, location=wujianhua_location):
    print("Beginning the provisioing of the virtual network - {}\n\n".format(wujianhua_resource_group))
    network_client = NetworkManagementClient(
        AzureServicePrincipalcredentials,
        subscription_id
    )

    vnet_name = resource_group + 'vNet'  # the name of virtual network

    async_virtual_network = network_client.virtual_networks.create_or_update(
        resource_group,  # the name of resource group within which this resource would be provisioned
        vnet_name,
        {
            'location': location,
            'address_space': {
                'address_prefixes': [wujianhua_network_prefix + '.0.0/16']  # Of course, you can parameterize the CIDR value of your Virtual Networks
             }
        }
    )

    async_virtual_network.wait()

# create a common subnet for general purpose. This is not REQUIRED by Azure, however,
# normally, you would create a subnet for general purpose in your vNet/vNets
    async_common_subnet = network_client.subnets.create_or_update(
        resource_group,
        vnet_name,
        "wujianhuaCommon",  # the name of this subnet. You don't have to hard code this value
        {
            'address_prefix': wujianhua_network_prefix + '.0.0/24'
        }
    )

    async_common_subnet.wait()

# you VM will be in this subnet
    async_vm_subnet = network_client.subnets.create_or_update(
        resource_group,  # the name of resource group within which this resource would be provisioned
        vnet_name,  # the name of virtual network
        "wujianhuaVM",  # the name of this subnet. we will put our VM in this subnet
        {
            'address_prefix': wujianhua_network_prefix + '.1.0/24'
        }
    )
    async_vm_subnet.wait()

# in a setup where there is Azure Application Gateway in front of your VM, then, in general, we would
# create a seperated vNet subnet for accomendating Application Gateway resource
    async_appGateway_subnet = network_client.subnets.create_or_update(
        resource_group,
        vnet_name,
        "wujianhuaAppGateway",
        {
            'address_prefix': wujianhua_network_prefix + '.2.0/24'
        }
    )
    async_appGateway_subnet.wait()

# this is a special subnet called GatewaySubnet. It has to be named this way.
# For detail, pls refer to Microsoft's online Azure documentation at:
# https://docs.microsoft.com/en-us/office365/enterprise/designing-networking-for-microsoft-azure-iaas#step-5-determine-the-subnets-within-the-vnet-and-the-address-spaces-assigned-to-each
    async_gateway_subnet = network_client.subnets.create_or_update(
        resource_group,
        vnet_name,
        "GatewaySubnet",
        {
            'address_prefix': wujianhua_network_prefix + '.3.0/24'
        }
    )
    async_gateway_subnet.wait()

# get the id of the subnet for virtual machines
    vm_subnet_id = async_vm_subnet.result().id
    return vm_subnet_id


def wujianhua_NetworkInt(AzureServicePrincipalcredentials=AzureServicePrincipalcredentials, subscription_id=wujianhua_subscription_id, resource_group=wujianhua_resource_group, location=wujianhua_location, vm_subnet_id=None):
    # provision a network interface for VM.
    print("Beginning the provisioing of the network interface - {}\n\n".format(wujianhua_resource_group))
    network_client = NetworkManagementClient(
        AzureServicePrincipalcredentials,
        subscription_id
    )

    public_ip_address_name = "wujianhuaPubIPAddress"  # the name of public IP address

    async_public_ip_address = network_client.public_ip_addresses.create_or_update(
        resource_group,
        public_ip_address_name,
        {
            "location": location,
            "sku": {
                "name": "Basic"
            },
            "public_ip_allocation_method": "Dynamic",
            "public_ip_address_version": "IPv4"

        }
    )

    async_public_ip_address.wait()

    publicIPAddress = network_client.public_ip_addresses.get(
        resource_group,
        public_ip_address_name,
    )

    async_network_interface = network_client.network_interfaces.create_or_update(
        resource_group,
        'wujianhuaint',
        {
            "location": location,
            "ip_configurations": [{
                "name": "wujianhua",
                "subnet": {
                    "id": vm_subnet_id
                },
                "public_ip_address": publicIPAddress
            }]
        }
    )

    async_network_interface.wait()

    network_int_id = async_network_interface.result().id
    return network_int_id


def wujianhua_VM(AzureServicePrincipalcredentials=AzureServicePrincipalcredentials, subscription_id=wujianhua_subscription_id, resource_group=wujianhua_resource_group, location=wujianhua_location, network_int_id=None, vm_size=None):
    print("Beginning the provisioing of the virtual machine in the resource group - {}\n\n".format(wujianhua_resource_group))
    print("the id of network interface is:" + network_int_id)
    compute_client = ComputeManagementClient(
        AzureServicePrincipalcredentials,
        wujianhua_subscription_id
    )

    async_vm = compute_client.virtual_machines.create_or_update(
        resource_group,  # the name of resource group within which this resource would be provisioned
        "wujianhua" + "-openCloudDevops",  # the name of your virtual machines
        {
           'location': location,
           'tags': { 'Name':'wujianhuaVM' },
           'hardware_profile': {
                'vm_size': vm_size
           },
           'storage_profile': {
                "image_reference": {
                    "publisher": "Canonical",
                    "offer": "UbuntuServer",
                    "sku": "18.04-LTS",
                    "version": "latest"
                },
                'os_disk': {
                    'name': "wujianhuaVM-managed-disk",
                    "caching": "ReadWrite",
                    "create_option": "FromImage",
                    'disk_size_gb': "100",
                    "managed_disk": {
                        "storage_account_type": "Premium_LRS"
                    }
                }
           },
           "os_profile": {
                "computer_name": "wujianhuavm",
                "admin_username": "Af123987123987",
                "admin_password": "Af123987123987"
           },
           "network_profile": {
                "network_interfaces": [ {
                    "id": network_int_id
                } ]
           }
         }
    )

    async_vm.wait()

if __name__ == "__main__":
    wujianhua_rg(
        resource_group = wujianhua_resource_group,
        location = wujianhua_location
    )

    vm_subnet_id = wujianhua_vNet(
        AzureServicePrincipalcredentials = AzureServicePrincipalcredentials,
        subscription_id = wujianhua_subscription_id,
        resource_group = wujianhua_resource_group,
        location = wujianhua_location
    )

    network_int_id = wujianhua_NetworkInt(
        AzureServicePrincipalcredentials = AzureServicePrincipalcredentials,
        subscription_id = wujianhua_subscription_id,
        resource_group = wujianhua_resource_group,
        location = wujianhua_location,
        vm_subnet_id = vm_subnet_id
    )

    wujianhua_VM(
        AzureServicePrincipalcredentials = AzureServicePrincipalcredentials,
        subscription_id = wujianhua_subscription_id,
        resource_group = wujianhua_resource_group,
        location = wujianhua_location,
        network_int_id = network_int_id,
        vm_size = wujianhua_vmSize
        )
