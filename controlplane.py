
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

class cts_test:

    def __init__(self, device):
        self.device = device
        self.ctscred = None
        self.ctsradiusserver = None
        self.ctsradiusstate = None
        self.ctspac = None
        self.pacrefresh = None
        self.ctsenvstatus = None
        self.ctslocalsgt = None


    #Layer 2 (MAC) Control Plane Query
    def cts_cp(self, service):

        devbulk = service.inventory[self.device]

        ctscred_cmd = "show cts credentials"
        ctspac_cmd = "show cts pac"
        ctsradius_cmd = "show run | se radius dnac-client-radius-group"
        ctsenv_cmd = "show cts environment-data | se Installed|Local|status"

        print ("Validating the CTS Control Plane...")
        print ("Retrieving information of device {}".format(self.device))

        try:
            commands1 = devbulk.exec([ctscred_cmd,ctspac_cmd,ctsradius_cmd,ctsenv_cmd]).wait()
        except (IndexError, ValueError):
            sys.exit("Unable to fetch configuration from device {}".format(self.mgmtip))

        ctscred_op = commands1.result["{}".format(ctscred_cmd)].data
        ctspac_op = commands1.result["{}".format(ctspac_cmd)].data
        ctsradius_op = commands1.result["{}".format(ctsradius_cmd)].data
        cstenv_op = commands1.result["{}".format(ctsenv_cmd)].data


        #Validating Local CTS Credentials:
        for line in ctscred_op.splitlines():
            if "No CTS credentials" in line:
                self.ctscred == None
                print ("WARNING! No CTS Credentials found for this device, CTS control plane might be incomplete/empty")
            if "CTS password" in line:
                self.ctscred == re.compile("(?<=\=).*").search(line).group().strip()
        #Validating CTS PAC:
        for line in ctspac_op.splitlines():
            if  "No PACs" in line:
                print ("WARNING! No CTS PAC found for this device!")
                self.ctspac == None
            if "AID" in line:
                self.ctspac == True
            if "Refresh timer stopped" in line:
                self.pacrefresh == "Expired"
                print ("WARNING!, CTS PAC found but its in expired state, please wait for CTS server validation")
            if "Refresh timer is set" in line:
                self.pacrefresh == re.compile("(?<=for).*").search(line).group().strip()

        for line in ctsradius_cmd.splitlines():
            if "server"ha e
