from dataclasses import dataclass
import radkit_client
import ipaddress
import re
import sys
import radkit_cli
import ipverifications
import device_profiler
import hostonboarding
import forwardinglogic
#import controlplane

from radkit_client.sync import (
    create_context
)

def startup():
    email = "jalejand@cisco.com"
    domain = "PROD"
    string = "qzjr-mk34-gk8c"
    service = radkit_cli.radkit_login(email,domain,string)
    return (service)

def initial_setup():

    
    #Saved Variables for Faster Execution
    devicelist = {0: {'Name': 'fiab-lab2-virtualpod-mxc5-com', 'Host': '172.12.0.7', 'Type': 'IOS', 'Loopback0': '172.12.1.80'}, 1: {'Name': 'border2-virtualpod-mxc5-com', 'Host': '172.12.0.2', 'Type': 'IOS', 'Loopback0': '172.12.1.66'}, 2: {'Name': 'localcp-virtualpod-mxc5-com', 'Host': '172.12.0.30', 'Type': 'IOS', 'Loopback0': '172.12.1.123'}, 3: {'Name': 'edge1-virtualpod-mxc5-com', 'Host': '172.12.0.3', 'Type': 'IOS', 'Loopback0': '172.12.1.72'}, 4: {'Name': 'border1-virtualpod-mxc5-com', 'Host': '172.12.0.1', 'Type': 'IOS', 'Loopback0': '172.12.1.65'}, 5: {'Name': 'wlc-virtualpod-mxc5-com', 'Host': '172.12.1.252', 'Type': 'IOS', 'Loopback0': None}, 6: {'Name': 's1-border-virtualpod-mxc5-com', 'Host': '172.12.0.9', 'Type': 'IOS', 'Loopback0': '172.12.1.100'}, 7: {'Name': 'edge2-virtualpod-mxc5-com', 'Host': '172.12.0.4', 'Type': 'IOS', 'Loopback0': '172.12.1.73'}, 8: {'Name': 'fiab-lab3-virtualpod-mxc5-com', 'Host': '172.12.0.6', 'Type': 'IOS', 'Loopback0': '172.12.1.90'}, 9: {'Name': 'tcp-virtualpod-mxc5-com', 'Host': '172.12.0.100', 'Type': 'IOS', 'Loopback0': '172.12.0.100'}, 10: {'Name': 'border8kv-virtualpod-mxc5-com', 'Host': '172.12.1.101', 'Type': 'IOS', 'Loopback0': '172.12.1.101'}}

    #device_source_ip = ipverifications.ip_validator_input("Inventory Management IP address of Source Fabric Device (Edge or L2 Border) > ")
    device_source_ip = "172.12.0.3"
    #endpoint_ip = ip_parser("Endpoint source IP >")
    endpoint_ip = "172.12.10.6"
    #destination_ip = ip_parser("Destination IP >")
    destination_ip = "172.12.10.123"

    #Add the management IP subnet of the fabric site in Catalyst Center, all fabric devices must be within these subnets
    #You can use multiple subnets to scope the fabric separated by commas, ex: 172.12.0.0/16, 172.16.0.0/16, 172.12.1.72/32
    #Restrict it as much as possible.

    subnets = "172.12.0.0/16, 172.12.1.65/32"
    validatedsubnet = ipverifications.stringvalidator(subnets)
    #devicelist = device_profiler.fabric_builder(validatedsubnet,service)

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

    #Extract CPs and convert them into hostnames:
    l2cp_list = sourceep.l2cps
    l3cp_list = sourceep.l3cps
    l2cps = []
    l3cps = []
    for i in devicelist:
        lo0 = devicelist[i]['Loopback0']
        mgmt = devicelist[i]['Host']
        try:
            if  any(x in lo0 for x in l2cp_list):
                l2cps.append(mgmt)
            if  any(x in lo0 for x in l3cp_list):
                l3cps.append(mgmt)
        except:
            pass
    print (l2cps)
    print (l3cps)

    #Flow Type Determination
    #results = forwardinglogic.flowelection(sourceep,destination_ip
    #Same Subnet Verification
   

    """
    Validations
    #border = border1-pod2-com, ins 8190 5ce1.7629.0928
    #""172.19.1.72", "5254.0000.c5c3", "8189", "control-plane-lastorder-com""
    res = controlplane.cp_state("172.19.1.72", "5ce1.7629.0928", "8190", "border1-pod2-com")
    res.l3_state(service)
    print (res.__dict__)
    #edge 1 edge1-pod2-com as ETR, 172.19.1.65 as queriedcpip
    res = controlplane.cp_etr_state("172.19.1.65", "edge1-pod2-com")
    res.session_state(service)
    print (res.__dict__)
    res = controlplane.route_recursion("172.12.1.73", "edge1-virtualpod-mxc5-com")
    res.rloc_data(service)  
    print (res.__dict__)

    for i in res.phy:
        des = controlplane.underlay_validations(i, "edge1-virtualpod-mxc5-com")
        des.intf_parse(service)
        print(des.__dict__)
    """


if __name__ == "__main__":
    with create_context():
        global service

        service = startup()
        initial_setup()
