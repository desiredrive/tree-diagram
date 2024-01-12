from dataclasses import dataclass
import radkit_client
import ipaddress
import re
import sys
import radkit_cli
import ipverifications
import device_profiler
import hostonboarding

from radkit_client.sync import (
    create_context
)

def startup():
    email = "your_mail"
    domain = "PROD"
    string = "your_string"
    service = radkit_cli.radkit_login(email,domain,string)
    return (service)

def initial_setup():


    #device_source_ip = ipverifications.ip_validator_input("Inventory Management IP address of Source Fabric Device (Edge or L2 Border) > ")
    device_source_ip = "172.12.0.3"
    #endpoint_ip = ip_parser("Endpoint source IP >")
    endpoint_ip = "172.12.10.111"
    #destination_ip = ip_parser("Destination IP >")
    destination_ip = "172.12.10.123"

    #Add the management IP subnet of the fabric site in Catalyst Center, all fabric devices must be within these subnets
    #You can use multiple subnets to scope the fabric separated by commas, ex: 172.12.0.0/16, 172.16.0.0/16, 172.12.1.72/32
    #Restrict it as much as possible.
    #mgmtsubnet = "172.12.0.0"
    #mask = "16"
    validatedsubnet = ipverifications.subnetvalidation(mgmtsubnet,mask)
    #devicelist = device_profiler.fabric_builder(validatedsubnet)
    #devicelist.allmappings(service)
    #print (devicelist.fabric_list)

    #Profiling device where the Source is Located
    print ("Profiling device where the Source is Located...")
    xtr = device_profiler.device(device_source_ip)
    xtr.profile_device(service)
    print (xtr.__dict__)

    #Gathering information about the source...
    print ("Gathering information about the source...")
    sourceep = hostonboarding.endpoint_info(endpoint_ip)
    sourceep.host_onboarding_validation(xtr,service)
    print (sourceep.__dict__)
    #source_endpoint = hostonboarding.hostverification(endpoint_ip,source_device,service)
    #print (source_endpoint.__dict__)


if __name__ == "__main__":
    with create_context():
        global service

        service = startup()
        initial_setup()
