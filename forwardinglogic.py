import re
import ipverifications
import sys

#Switching Flow  : From one LISP XTR to Another
'''
Verifications:

Are source and destination in the same subnet? If Yes:
    Are these in an L2 only network? - 1st Exception, Check L2 only flag
    Is Flood ARPnd Enabled? - 
        Yes - Verification of L2 AR LISP is marked as strict 
        No - Verification of L2 AR LISP is only to find remote RLOCs
            If remote RLOCs cannot be found (missing AR), an exception must be performed - Request Destination MAC of the endpoint
            If remote RLOCs cannot be found (missing MAC), an exception must be performed - Request Destination device (mgmtip) to perform Host Onboarding Validations
    if L2 only: SGT and DHCP operations must be performed differently
    CP queries:
        if Flood ARPnd disabled : L2MAC and L2AR are mandatory
        if Flood ARPnd enabled: L2MAC is mandatory, L2AR is relaxed
'''
def flowelection(epinfo, dstip):
    issamesubnet=ipverifications.subnet_validator(epinfo.sourceip,dstip,epinfo.mask)
    print (epinfo.sourceip)
    if issamesubnet==False:
        print ("Devices in different Subnet, Routing Flow")
    if issamesubnet==True:
        print ("Devices in the same Subnet, Switching Flow")
        results = switchingflow(epinfo,dstip)

def switchingflow(epinfo, dstip):
    l2onlystate = epinfo.isl2only
    floodarp = epinfo.arpflood
    #Triggering CP queriers from here.