
from dataclasses import dataclass
import re
import sys
import radkit_cli
from device_profiler import device, finddevice

class cts_info:

    def __init__(self, srcep, dstep, device):
        self.srcip = None
        self.dstip = None
        self.srcvlan = None
        self.dstvlan = None
        self.srcvrf = None
        self.dstvrf = None
        self.srcsgtnum = None 
        self.dstsgtnum = None


        #Initialization
        if dstep.isl2only == True:
            self.dstvrf = "Default"
        else:
            self.dstvrf = dstep.sourcevrf
        
        self.srcip = srcep.sourceip 
        self.dstip = dstep.sourceip

        self.srcvlan = srcep.sourcevlan 
        self.dstvlan = dstep.sourcevlan

        self.srcvrf = srcep.sourcevrf
        self.srcsgtnum = srcep.sgt 
        self.dstsgtnum = dstep.sgt 


    #Layer 2 (MAC) Control Plane Query
    def enforcement(self, service):
        self.dstep.mgmtip = mgmtip 
        inith =  finddevice(mgmtip)
        inith.find_device(service)
        hostname = inith.hostname

        #Validating Global Enforcement on Destination Device
        ctsenf_cmd = "show run | i role-based enfo"
        ctsdef_cmd = "show cts role-based enforcement default"
        ctsrule_cmd = "show cts role-based enforcement from {} to {}".format(self.srcsgtnum, self.dstsgtnum)
        ctscnt_cmd = "show cts role-based counters from {} to {}".format(self.srcsgtnum, self.dstsgtnum)

        
        self.globalenforcement = None



        self.vlanenforcement = None
        self.sgtbinding = None

        self.rbacl = None
        self.defaultrule = None
        self.counters = None
