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
from pprint import pformat

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
    #devicelist = {0: {'Name': 'fiab-lab2-virtualpod-mxc5-com', 'Host': '172.12.0.7', 'Type': 'IOS', 'Loopback0': '172.12.1.80'}, 1: {'Name': 'border2-virtualpod-mxc5-com', 'Host': '172.12.0.2', 'Type': 'IOS', 'Loopback0': '172.12.1.66'}, 2: {'Name': 'localcp-virtualpod-mxc5-com', 'Host': '172.12.0.30', 'Type': 'IOS', 'Loopback0': '172.12.1.123'}, 3: {'Name': 'edge1-virtualpod-mxc5-com', 'Host': '172.12.0.3', 'Type': 'IOS', 'Loopback0': '172.12.1.72'}, 4: {'Name': 'border1-virtualpod-mxc5-com', 'Host': '172.12.0.1', 'Type': 'IOS', 'Loopback0': '172.12.1.65'}, 5: {'Name': 'wlc-virtualpod-mxc5-com', 'Host': '172.12.1.252', 'Type': 'IOS', 'Loopback0': None}, 6: {'Name': 's1-border-virtualpod-mxc5-com', 'Host': '172.12.0.9', 'Type': 'IOS', 'Loopback0': '172.12.1.100'}, 7: {'Name': 'edge2-virtualpod-mxc5-com', 'Host': '172.12.0.4', 'Type': 'IOS', 'Loopback0': '172.12.1.73'}, 8: {'Name': 'fiab-lab3-virtualpod-mxc5-com', 'Host': '172.12.0.6', 'Type': 'IOS', 'Loopback0': '172.12.1.90'}, 9: {'Name': 'tcp-virtualpod-mxc5-com', 'Host': '172.12.0.100', 'Type': 'IOS', 'Loopback0': '172.12.0.100'}, 10: {'Name': 'border8kv-virtualpod-mxc5-com', 'Host': '172.12.1.101', 'Type': 'IOS', 'Loopback0': '172.12.1.101'}}
    devicelist = {0: {'Name': 'fiab-pod2-com', 'Host': '172.19.1.80', 'Type': 'IOS', 'Loopback0': '172.19.1.80'}, 1: {'Name': 's1petr-pod2-com', 'Host': '172.19.1.75', 'Type': 'IOS', 'Loopback0': '172.19.1.75'}, 2: {'Name': 'c18-pod2-com', 'Host': '172.19.1.101', 'Type': 'IOS', 'Loopback0': None}, 3: {'Name': 'border1-pod2-com', 'Host': '172.19.1.65', 'Type': 'IOS', 'Loopback0': '172.19.1.65'}, 4: {'Name': 'middle-pod2-com', 'Host': '172.19.1.102', 'Type': 'IOS', 'Loopback0': None}, 5: {'Name': 'a52-pod2-com', 'Host': '172.19.1.103', 'Type': 'IOS', 'Loopback0': None}, 6: {'Name': 'border2-pod2-com', 'Host': '172.19.1.66', 'Type': 'IOS', 'Loopback0': '172.19.1.66'}, 7: {'Name': 'edge1-pod2-com', 'Host': '172.19.1.72', 'Type': 'IOS', 'Loopback0': '172.19.1.72'}, 8: {'Name': 'switch-172-19-1-74-pod2-com', 'Host': '172.19.1.74', 'Type': 'IOS', 'Loopback0': '172.19.1.74'}, 9: {'Name': 'edge2-pod2-com', 'Host': '172.19.1.73', 'Type': 'IOS', 'Loopback0': '172.19.1.73'}}
    #device_source_ip = ipverifications.ip_validator_input("Inventory Management IP address of Source Fabric Device (Edge or L2 Border) > ")
    device_source_ip = "172.19.1.73"
    #endpoint_ip = ip_parser("Endpoint source IP >")
    endpoint_ip = "172.19.10.35"
    #destination_ip = ip_parser("Destination IP >")
    destination_ip = "172.19.10.2"

    #Add the management IP subnet of the fabric site in Catalyst Center, all fabric devices must be within these subnets
    #You can use multiple subnets to scope the fabric separated by commas, ex: 172.12.0.0/16, 172.16.0.0/16, 172.12.1.72/32
    #Restrict it as much as possible.

    subnets = "172.12.0.0/16, 172.12.1.65/32, 172.19.0.0/16"
    validatedsubnet = ipverifications.stringvalidator(subnets)
    #devicelist = device_profiler.fabric_builder(validatedsubnet,service)


    #Profiling device where the Source is Located
    print ("Profiling device where the Source is located...\n")
    xtr = device_profiler.device(device_source_ip)
    xtr.profile_device(service)
    print (pformat(vars(xtr), indent=4, width =1, sort_dicts=False))

    #Gathering information about the source...
    print ("Gathering information about the source endpoint...\n")
    sourceep = hostonboarding.endpoint_info(endpoint_ip)
    sourceep.host_onboarding_validation(xtr,service)
    print (pformat(vars(sourceep), indent=4, width =1, sort_dicts=False))

    #Extract CPs and convert them into hostnames:
    l2cp_list = sourceep.l2cps
    l3cp_list = sourceep.l3cps
    l2cps = []
    l3cps = []
    for i in devicelist:
        lo0 = devicelist[i]['Loopback0']
        mgmt = devicelist[i]['Name']
        try:
            if  any(x in lo0 for x in l2cp_list):
                l2cps.append(mgmt)
            if  any(x in lo0 for x in l3cp_list):
                l3cps.append(mgmt)
        except:
            pass

    #Flow Type Determination
    result = forwardinglogic.flowelection(sourceep,destination_ip)
    #Same Subnet Verification
    if result == "L2":
        l2_flow = forwardinglogic.switchingflow(sourceep,destination_ip,service,l2cps)
        dest_mac = l2_flow[0]
        dest_rloc = l2_flow[1]
        src_rloc = sourceep.rloc

        #Intra-XTR L2 Local Execution:
        if sourceep.rloc == dest_rloc:
            print ("Host {} and {} are in the same XTR {}, performing local checks \n".format(endpoint_ip,destination_ip,dest_rloc))
        
        #Inter-XTR L2 East West Execution.1
        else:
            print ("Host {} is in RLOC {} and Host {} is in RLOC {} \n".format(endpoint_ip, src_rloc, destination_ip,dest_rloc))
            for i in devicelist:
                lo0 = devicelist[i]['Loopback0']
                if lo0 == dest_rloc:
                    mgmt = devicelist[i]['Host']
            forwardinglogic.l2_east_west(xtr.hostname,sourceep,dest_mac,dest_rloc,destination_ip,mgmt,service)
            

if __name__ == "__main__":
    with create_context():
        global service

        service = startup()
        initial_setup()
