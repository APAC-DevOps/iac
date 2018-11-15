import os
import sys
import argparse
import subprocess
import requests
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
# Create Application Gateway
def agri_Api_AppGateway(envName, agri_site_fqdn, AzureServicePrincipalcredentials, subscription_id, resource_group, location='AustraliaEast'):
    network_client = NetworkManagementClient(AzureServicePrincipalcredentials, subscription_id)

    async_network_client = network_client.virtual_networks.create_or_update(
        resource_group,
        resource_group + 'Vnet',
        {
            'location': location,
            'address_space': {
                'address_prefixes': ['10.64.0.0/16']
             }
        }
    )

    async_network_client.wait()

    async_common_subnet = network_client.subnets.create_or_update(
        resource_group,
        resource_group + 'Vnet',
        "AgriCommon",
        {
            'address_prefix': '10.64.0.0/24'
        }
    )

    async_function_subnet = network_client.subnets.create_or_update(
        resource_group,
        resource_group + 'Vnet',
        "AgriFunctionAPI",
        {
            'address_prefix': '10.64.1.0/24'
        }
    )

    async_appGateway_subnet = network_client.subnets.create_or_update(
        resource_group,
        resource_group + 'Vnet',
        "AgriAPIAppGateway",
        {
            'address_prefix': '10.64.2.0/24'
        }
    )

    async_gateway_subnet = network_client.subnets.create_or_update(
        resource_group,
        resource_group + 'Vnet',
        "GatewaySubnet",
        {
            'address_prefix': '10.64.3.0/24'
        }
    )

    AppGW_Subnet_Id = async_appGateway_subnet.result().id



    # Create Public IPv4 Address
    async_appGW_frontend_public_IP_Addr = network_client.public_ip_addresses.create_or_update(
       resource_group,
       resource_group + "AppGatewayFrontendPublicIPAddr",
       {
           'location': location,
            "sku": {
                "name": "Basic"
            },
           'public_ip_allocation_method': "Dynamic",
           'public_ip_address_version': "IPv4",
       }
    )
    Frontend_Public_IP_Configure_Id = async_appGW_frontend_public_IP_Addr.result().id

    resource_client = ResourceManagementClient(AzureServicePrincipalcredentials, subscription_id)


    print("\nInitializing the deployment with subscription id: {}, resource group: {}\n".format(subscription_id, resource_group))

    async_resource_group = resource_client.resource_groups.get(
        resource_group
    )

    resource_group_id = async_resource_group.id

    # Create Application Gateway
    print('\nCreating Application Gateway...')
    AgriAPIAppGatewayName = resource_group + 'AppGateway'
    appgateway_id = resource_group_id + '/providers/Microsoft.Network/applicationGateways/' + AgriAPIAppGatewayName
    appgateway_public_frontip_name = resource_group + "PublicInterfaceIPv4Addr"
    # appgateway_private_frontip_name = "PrivateInterfaceIPv4Addr"
    FrontPort_Http80 = "HTTP80"
    FrontPort_Https443 = "HTTPS443"
    FrontPort_Http8080 = "HTTP8080"


# Define Listeners
    api_http_listener = "ApiHTTPListener"
    api_https_listener = "ApiHTTPSListener"
    api_http8080_listener = "ApiHTTP8080Listener"
    ous_http_listener = "OusHTTPListener"
    ous_https_listener = "OusHTTPSListener"

#  Define backend pool name
    api_backend_pool = "api_web_app"
    ous_backend_pool = "ous_web_app"


# define backend http settings
    appgateway_backend_http_settings_name = "appGatewayBackendHttpSettings"
    appgateway_backend_https_settings_name = "appGatewayBackendHttpSSLSettings"
    appgateway_backend_http_settings_ous = "appGatewayBackendHttpSettingsDevOus"
    appgateway_backend_https_settings_ous = "appGatewayBackendHttpSSLSettingsDevOus"


# define path maps
    api_http_url_path_maps = "ApiHttpUrlPathMaps"
    api_https_url_path_maps = "ApiHttpsUrlPathMaps"
    ous_http_url_path_maps = "OusHttpUrlPathMaps"
    ous_https_url_path_maps = "OusHttpsUrlPathMaps"


# define probes
    agri_api_web_app_http_probe_name = "AgriApiHttpWebAppProbe"
    agri_api_web_app_https_probe_name = "AgriApiHttpsWebAppProbe"
    agri_ous_web_app_http_probe_name = "AgriOusHttpWebAppProbe"
    agri_ous_web_app_https_probe_name = "AgriOusHttpsWebAppProbe"


# define rule name
    api_http_path_based_rule = "ApiHttp"
    api_https_path_based_rule = "ApiHttps"
    api_http8080_path_based_rule = "ApiHttp8080"
    ous_http_path_based_rule = "OusHttp"
    ous_https_path_based_rule = "OusHttps"


# define listner DNS name
    api_agri_fqdn = envName + "-api.agridigital.io"
    ous_agri_fqdn = envName + "-ous.agridigital.io"


# define backend pool hosts name
    api_azure_fqdn = agri_site_fqdn[0]
    ous_azure_fqdn = agri_site_fqdn[1]

    wildcast_ssl_cert_name = "agridigital-io.cer"


# create or update application gateway
    async_ag_creation = network_client.application_gateways.create_or_update(
        resource_group,
        AgriAPIAppGatewayName,
        {
            'location': location,
            "sku": {
                "name": "WAF_Medium",
                "tier": "WAF",
                "capacity": 1
            },
            "web_application_firewall_configuration": {
                "enabled": True,
                "firewall_mode": "Detection",
                "rule_set_type": "OWASP",
                "rule_set_version": "3.0",
                "disabled_rule_groups": [{
                    "rule_group_name": "REQUEST-942-APPLICATION-ATTACK-SQLI",
#                    "rules": [942200, 942260, 942340, 942370]
                    }
                ]
            },
            "ssl_certificates": [{
                "name": wildcast_ssl_cert_name,
                "password": "tWLBYgvhxnq9AweMQ5IyoScTPXa8jFCdmO1sDJ4RpGZurfi073",
                "data": "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"
            }],
            "gateway_ip_configurations": [{
                "name": "appGatewayIpConfig",
                "subnet": {
                    "id": AppGW_Subnet_Id
                }
            }],
            "frontend_ip_configurations": [{
                "name": appgateway_public_frontip_name,
                "public_ip_address": {
                    "id": Frontend_Public_IP_Configure_Id
                }
            }],
            "frontend_ports": [
            {
                "name": FrontPort_Http80,
                "port": 80
            },
            {
                "name": FrontPort_Https443,
                "port": 443
            },{
                "name": FrontPort_Http8080,
                "port": 8080
            }],

#Application Gateway Backend Address Pools
            "backend_address_pools": [
    # Define Backend Pool for Agri  Environment
            {
                "name": api_backend_pool,
                "backend_addresses": [{
                    "fqdn": api_azure_fqdn
                }]
            }, {
                "name": ous_backend_pool,
                "backend_addresses": [{
                    "fqdn": ous_azure_fqdn
                }]
            }
            ],

# # Application Gateway Probes for Agri API and OUS Components
            "probes": [
                {
                "name": agri_ous_web_app_http_probe_name,
                "protocol": "http",
                "path": "/api/_organisations/heartbeat",
                "interval": 80,
                "timeout": 120,
                "unhealthy_threshold": 3,
                "pick_host_name_from_backend_http_settings": True,
                "match": {
                    "status_codes": [ "200-399" ]
                }
            },
            {
                "name": agri_ous_web_app_https_probe_name,
                "protocol": "https",
                "path": "/api/_organisations/heartbeat",
                "interval": 80,
                "timeout": 120,
                "unhealthy_threshold": 3,
                "pick_host_name_from_backend_http_settings": True,
                "match": {
                    "status_codes": [ "200-399" ]
                }
            },
            {
                "name": agri_api_web_app_http_probe_name,
                "protocol": "http",
                "path": "/api",
                "interval": 80,
                "timeout": 120,
                "unhealthy_threshold": 3,
                "pick_host_name_from_backend_http_settings": True,
                "match": {
                    "status_codes": [ "200-399" ]
                }
            },
            {
                "name": agri_api_web_app_https_probe_name,
                "protocol": "https",
                "path": "/api",
                "interval": 80,
                "timeout": 120,
                "unhealthy_threshold": 3,
                "pick_host_name_from_backend_http_settings": True,
                "match": {
                    "status_codes": [ "200-399" ]
                }
            }
            ],

#Backend HTTP Collections for API and OUS components
            "backend_http_settings_collection": [
            {
                "name": appgateway_backend_http_settings_ous,
                "port": 80,
                "protocol": "Http",
                "cookie_based_affinity": "Enabled",
                "request_timeout": 360,
                "pick_host_name_from_backend_address": True,
                "probe": {
                    "id": appgateway_id + "/probes/" + agri_ous_web_app_http_probe_name
                }
            },
            {
                "name": appgateway_backend_https_settings_ous,
                "port": 443,
                "protocol": "Https",
                "cookie_based_affinity": "Enabled",
                "request_timeout": 360,
                "pick_host_name_from_backend_address": True,
                "probe": {
                    "id": appgateway_id + "/probes/" + agri_ous_web_app_https_probe_name
                }
            },
            {
                "name": appgateway_backend_http_settings_name,
                "port": 80,
                "protocol": "Http",
                "cookie_based_affinity": "Enabled",
                "request_timeout": 360,
                "pick_host_name_from_backend_address": True,
                "probe": {
                    "id": appgateway_id + "/probes/" + agri_api_web_app_http_probe_name
                }
            },
            {
                "name": appgateway_backend_https_settings_name,
                "port": 443,
                "protocol": "Https",
                "cookie_based_affinity": "Enabled",
                "request_timeout": 360,
                "pick_host_name_from_backend_address": True,
                "probe": {
                    "id": appgateway_id + "/probes/" + agri_api_web_app_https_probe_name
                }
            }],

# HTTP Listeners Definition
            "http_listeners": [
    # Begin HTTP Listeners Definition For Agri  Environment
            {
                "name": api_http_listener,
                "frontend_ip_configuration": {
                    "id": appgateway_id + "/frontendIPConfigurations/" + appgateway_public_frontip_name
                },
                "frontend_port": {
                    "id": appgateway_id + '/frontendPorts/' + FrontPort_Http80
                },
                "protocol": "Http",
                "host_name": api_agri_fqdn,
                "ssl_certificate": None
            },
            {
                "name": api_https_listener,
                "frontend_ip_configuration": {
                    "id": appgateway_id + "/frontendIPConfigurations/" + appgateway_public_frontip_name
                },
                "frontend_port": {
                    "id": appgateway_id + '/frontendPorts/' + FrontPort_Https443
                },
                "protocol": "Https",
                "host_name": api_agri_fqdn,
                "ssl_certificate": {
                    "id": appgateway_id + "/sslCertificates/" + wildcast_ssl_cert_name
                }
            }, {
                "name": api_http8080_listener,
                "frontend_ip_configuration": {
                    "id": appgateway_id + "/frontendIPConfigurations/" + appgateway_public_frontip_name
                },
                "frontend_port": {
                    "id": appgateway_id + '/frontendPorts/' + FrontPort_Http8080
                },
                "protocol": "Http",
                "host_name": api_agri_fqdn,
                "ssl_certificate": None
            },
            # {
            #     "name": ous_http_listener,
            #     "frontend_ip_configuration": {
            #         "id": appgateway_id + "/frontendIPConfigurations/" + appgateway_public_frontip_name
            #     },
            #     "frontend_port": {
            #         "id": appgateway_id + '/frontendPorts/' + FrontPort_Http80
            #     },
            #     "protocol": "Http",
            #     "host_name": ous_agri_fqdn,
            #     "ssl_certificate": None
            # },
            {
                "name": ous_https_listener,
                "frontend_ip_configuration": {
                    "id": appgateway_id + "/frontendIPConfigurations/" + appgateway_public_frontip_name
                },
                "frontend_port": {
                    "id": appgateway_id + '/frontendPorts/' + FrontPort_Https443
                },
                "protocol": "Https",
                "host_name": ous_agri_fqdn,
                "ssl_certificate": {
                    "id": appgateway_id + "/sslCertificates/" + wildcast_ssl_cert_name
                }
            }
            ],

# URL Path Maps Definition
            "url_path_maps": [
    #  Ous URL Path Maps
            # {
            #     "name": ous_http_url_path_maps,
            #     "default_backend_address_pool": {
            #         "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
            #     },
            #     "default_backend_http_settings": {
            #         "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_http_settings_ous
            #     },
            #     "path_rules": [{
            #         "name": "OusBankAccounts",
            #         "paths": [ '/api/_bank-accounts*' ],
            #         "backend_address_pool": {
            #             "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
            #         },
            #         "backend_http_settings": {
            #             "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_http_settings_ous
            #         }
            #     }]
            # },
            {
                "name": ous_https_url_path_maps,
                "default_backend_address_pool": {
                    "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
                },
                "default_backend_http_settings": {
                    "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_https_settings_ous
                },
                "path_rules": [{
                    "name": "OusBankAccounts",
                    "paths": [ '/api/_bank-accounts*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_https_settings_ous
                    }
                }]
            },

 #  Api URL Path Maps
            {
                "name": api_http_url_path_maps,
                "default_backend_address_pool": {
                    "id": appgateway_id + '/backendAddressPools/' + api_backend_pool
                },
                "default_backend_http_settings": {
                    "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_http_settings_name
                },
                "path_rules": [

                {
                    "name": "OusBankAccounts",
                    "paths": [ '/api/_bank-accounts*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_http_settings_ous
                    }
                }, {
                    "name": "OusUsers",
                    "paths": [ '/api/_users*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_http_settings_ous
                    }
                }, {
                    "name": "OusOrganisations",
                    "paths": [ '/api/_organisations*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_http_settings_ous
                    }
                },


                {
                    "name": "apiV1",
                    "paths": [ '/api/*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + api_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_http_settings_name
                    }
                },
                {
                    "name": "api",
                    "paths": [ '/*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + api_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_http_settings_name
                    }
                }]
            },
            {
                "name": api_https_url_path_maps,
                "default_backend_address_pool": {
                    "id": appgateway_id + '/backendAddressPools/' + api_backend_pool
                },
                "default_backend_http_settings": {
                    "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_https_settings_name
                },
                "path_rules": [

                {
                    "name": "OusBankAccounts",
                    "paths": [ '/api/_bank-accounts*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_https_settings_ous
                    }
                }, {
                    "name": "OusUsers",
                    "paths": [ '/api/_users*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_https_settings_ous
                    }
                }, {
                    "name": "OusOrganisations",
                    "paths": [ '/api/_organisations*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + ous_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_https_settings_ous
                    }
                },

                {
                    "name": "apiV1",
                    "paths": [ '/api/' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + api_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_https_settings_name
                    }
                },{
                    "name": "api",
                    "paths": [ '/*' ],
                    "backend_address_pool": {
                        "id": appgateway_id + '/backendAddressPools/' + api_backend_pool
                    },
                    "backend_http_settings": {
                        "id": appgateway_id + '/backendHttpSettingsCollection/' + appgateway_backend_https_settings_name
                    }
                }]
            }
            ],

# # Ruting Rules Definitions
            "request_routing_rules": [
    #   ous path based rule
            # {
            #     "name": ous_http_path_based_rule,
            #     "rule_type": "PathBasedRouting",
            #     "http_listener": {
            #         "id": appgateway_id + '/httpListeners/' + ous_http_listener
            #     },
            #     "url_path_map": {
            #         "id": appgateway_id + '/urlPathMaps/' + ous_http_url_path_maps
            #     }
            # },
            {
                "name": ous_https_path_based_rule,
                "rule_type": "PathBasedRouting",
                "http_listener": {
                    "id": appgateway_id + '/httpListeners/' + ous_https_listener
                },
                "url_path_map": {
                    "id": appgateway_id + '/urlPathMaps/' + ous_https_url_path_maps
                }
            },

    #   api path based rule
            # {
            #     "name": api_http_path_based_rule,
            #     "rule_type": "PathBasedRouting",
            #     "http_listener": {
            #         "id": appgateway_id + '/httpListeners/' + api_http_listener
            #     },
            #     "url_path_map": {
            #         "id": appgateway_id + '/urlPathMaps/' + api_http_url_path_maps
            #     }
            # },
            {
                "name": api_https_path_based_rule,
                "rule_type": "PathBasedRouting",
                "http_listener": {
                    "id": appgateway_id + '/httpListeners/' + api_https_listener
                },
                "url_path_map": {
                    "id": appgateway_id + '/urlPathMaps/' + api_https_url_path_maps
                }
            },
            {
                "name": api_http8080_path_based_rule,
                "rule_type": "PathBasedRouting",
                "http_listener": {
                    "id": appgateway_id + '/httpListeners/' + api_http8080_listener
                },
                "url_path_map": {
                    "id": appgateway_id + '/urlPathMaps/' + api_http_url_path_maps
                }
            }

            ]

        }
    )
    print_item(async_ag_creation.result())

    async_get_frontend_public_IP_Addr = network_client.public_ip_addresses.get(
       resource_group,
       resource_group + "AppGatewayFrontendPublicIPAddr",
    )

    print("the dns name from get public ip address is " + str(async_get_frontend_public_IP_Addr.dns_settings))
    print("the dns name from get public ip address is " + str(async_get_frontend_public_IP_Addr.dns_settings.fqdn))
    return async_get_frontend_public_IP_Addr.dns_settings.fqdn


def print_item(group):
    """Print an Azure object instance."""
    print("\tName: {}".format(group.name))
    print("\tId: {}".format(group.id))
    print("\tLocation: {}".format(group.location))
    print("\tTags: {}".format(group.tags))
    if hasattr(group, 'properties'):
        print_properties(group.properties)

def print_properties(props):
    """Print a ResourceGroup properties instance."""
    if props and props.provisioning_state:
        print("\tProperties:")
        print("\t\tProvisioning State: {}".format(props.provisioning_state))
    print("\n\n")
