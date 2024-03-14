
from dataclasses import dataclass
import re
import sys
import radkit_cli
from device_profiler import device, finddevice
import controlplane

def rulefinder(permissionop):
    matches1 = ["#", "show", "Role-based"]
    permsarray = []
    for i in permissionop.splitlines():
        if not any(x  in i for x in matches1):
            permsarray.append(i)
    permsarray = [i for i in permsarray if i]
    if len(permsarray) == 0:
            acluname = "Default Permit"
            dynaclflag = None
    elif len(permsarray) != 0:
        for line in permissionop.splitlines():
            if "Role-based" in line:
                rulename = line
                if "configured" in line:
                    dynaclflag = False
                else:
                    dynaclflag = True
        
        for line in permissionop.splitlines():
            if not any(x  in line for x in matches1):
                line = line.strip()
                if line != '':
                    if dynaclflag == False:
                        acluname = line.strip()
                    if dynaclflag == True:
                        aclname = line.split("-")
                        acluname = aclname[0]

    if acluname == None:
        sys.exit ("The following rule has no ACL downloaded or configured: {}".format(rulename))
    return (acluname,dynaclflag)

def tradaclparser(aclop):
    aces=[]
    matches = ["#", "show"]
    for line in aclop.splitlines():
        if not any(x  in line for x in matches):
            line = line.strip()
            if line != '':
                ace = line.split("(")
                ace = ace[0].strip()
                aces.append(ace)
    return (aces)

def rbaclparser(aclop):
    aces=[]
    matches = ["#", "show", "ACEs:"]
    for line in aclop.splitlines():
        if not any(x  in line for x in matches):
            line = line.strip()
            if line != '':
                aces.append(line)
    return (aces)

def ctscounters(ssgt, dsgt, default_flag,service,hostname):
    matches = ["#", "show"]
    if default_flag == False:
        cmd = "show cts role-based counters from {} to {} | ex From|Role".format(ssgt,dsgt)
    if default_flag == True:
        cmd = "show cts role-based counters default | ex From|Role"
    op = radkit_cli.get_any_single_output(hostname,cmd,service)
    for line in op.splitlines():
        if not any(x  in line for x in matches):
            if line != '':
                counters = re.split ("\s+", line)
                break
    countersd = {
                'From' : counters[0],
                'To' : counters[1],
                'SW Denied' : counters[2],
                'HW Denied' : counters[3],
                'SW Permit' : counters[4],
                'HW Permit' : counters[5],
                'SW Monitor' : counters[6],
                'HW Monitor' : counters[7]
                }

    return (countersd)

def ctsinterface(interface, service, hostname):
    matches = ["#", "show"]


    trust = "Untrusted"
    propagate = False
    sgt = 0
    intmatch = ['Ac', 'Tu', 'LISP', 'L2LISP']

    if 'Po' in interface:
        interfaces = controlplane.etherchannel_parse(service, interface, hostname)
    else: 
        interfaces = []
        interfaces.append(interface)
    cts = []
    for i in interfaces:
        if not any(x  in i for x in intmatch):
            cmd = "show cts interface {} | i Propagate|Peer|CTS".format(i)
            op = radkit_cli.get_any_single_output(hostname,cmd, service)

            for line in op.splitlines():
                    if not any(x  in line for x in matches):
                            if "CTS" in line:
                                    if "disabled" in line:
                                            mode = "DISABLED"
                                    if "enabled" in line:
                                            mode = re.compile("(?<=mode:).*").search(line).group().strip()
                            if "Peer SGT:" in line:
                                    sgt = re.compile("\d+").search(line).group().strip()
                            if "assignment:" in line:
                                    trust = re.compile("(?<=ment:).*").search(line).group().strip()
                            if "Propagate" in line:
                                    if "Enabled" in line:
                                        propagate = True
            ctsd = {
                'Mode' : mode,
                'Port SGT' : sgt,
                'Trust' : trust, 
                'Propagation' : propagate
            }

            cts.append(ctsd)
    return (cts)  
    
class cts_info:

    def __init__(self, srcep, dstep, device):
        self.globalenforcement = None
        self.vlanenforcement = None
        self.defaultrule = None
        self.specificrule = None
        self.counters = None 
        self.aclname = None
        self.aces = None
        self.ctsinterfaces = None
        self.dstep = dstep

        #Initialization
        if dstep.isl2only == True:
            self.dstvrf = "Default"
        else:
            self.dstvrf = dstep.sourcevrf
        
        if srcep.isl2only == True:
            self.scrvrf = srcep.sourcevrf
        else:
            self.scrvrf = srcep.sourcevrf

        self.srcip = srcep.sourceip
        self.dstip = dstep.sourceip

        self.srcvlan = srcep.sourcevlan
        self.dstvlan = dstep.sourcevlan
        
        self.srcsgtnum = srcep.sgt
        self.dstsgtnum = dstep.sgt

        self.hostname  = device

    def enforcement_flow(self, service):
        #Define main IOS Commands
        ctsenfcmd = 'show cts | i Enforce'
        ctsenfop = radkit_cli.get_any_single_output(self.hostname,ctsenfcmd,service)
        for line in ctsenfop.splitlines():
            if "Based Enforcement" in line:
                if "Enabled" in line:
                    self.globalenforcement = True
                else:
                    self.globalenforcement = False
            if "VLAN" in line:
                if "Enabled" in line:
                    ctsvlancmd = 'show run | i enforcement vlan'
                    ctsvlanop = radkit_cli.get_any_single_output(self.hostname,ctsvlancmd,service)
                    for line in ctsvlanop.splitlines():
                        if ctsvlanop == None:
                            self.vlanenforcement = False
                        else:
                            if "vlan-list" in line:
                                if self.dstvlan in line:
                                    self.vlanenforcement = True                
                else:
                    self.vlanenforcement = False              

    
        ctsspeccmd = 'show cts role-based  permissions from {} to {} | ex RBACL'.format(self.srcsgtnum,self.dstsgtnum)
        ctsspecop = radkit_cli.get_any_single_output(self.hostname,ctsspeccmd,service)
        aclpair = rulefinder(ctsspecop)
        aclname = aclpair[0]
        dynstate = aclpair[1]


        if aclname == "Default Permit":
            self.specificrule = False
            self.defaultrule = True
            ctsdefcmd = 'show cts role-based permissions default | ex RBACL'
            ctsdefop = radkit_cli.get_any_single_output(self.hostname,ctsdefcmd,service)
            aclpair = rulefinder(ctsdefop)
            aclname = aclpair[0]
            dynstate = aclpair[1]
            if aclname == "Default Permit":
                self.defaultrule = "Default Permit"
            else:
                if dynstate == True:
                    rbaclcmd = "show cts rbacl \"{}\" | se ACEs".format(aclname)
                    rbaclop = radkit_cli.get_any_single_output(self.hostname, rbaclcmd,service)
                    aces = rbaclparser(rbaclop)
                if dynstate == False:
                    aclcmd = "show ip access-list {} | ex Role".format(aclname)
                    aclop = radkit_cli.get_any_single_output(self.hostname, aclcmd,service)
                    aces = tradaclparser(aclop)
                self.aclname = aclname
                self.aces = aces
        else:
            self.specificrule = True
            self.defaultrule = False 
            if dynstate == True:
                rbaclcmd = "show cts rbacl \"{}\" | se ACEs".format(aclname)
                rbaclop = radkit_cli.get_any_single_output(self.hostname, rbaclcmd,service)
                aces = rbaclparser(rbaclop)
            if dynstate == False:
                aclcmd = "show ip access-list {} | ex Role".format(aclname)
                aclop = radkit_cli.get_any_single_output(self.hostname, aclcmd,service)
                aces = tradaclparser(aclop)
            self.aclname = aclname
            self.aces = aces           

        counters = ctscounters(self.srcsgtnum,self.dstsgtnum, self.defaultrule, service, self.hostname)
        self.counters = counters
        
        self.ctsinterfaces = ctsinterface(self.dstep.sourceport,service,self.hostname)

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

