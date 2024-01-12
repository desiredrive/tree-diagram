from dataclasses import dataclass
import radkit_client
import ipaddress
import re
import sys
from device_profiler import device, finddevice
import radkit_cli

class endpoint_info:

    def __init__(self,sourceip):
        self.sourceip = sourceip
        self.sourcemac = None
        self.sourcevlan = None
        self.sourcevrf = None
        self.sourceport = None
        self.ipdtmethod = None
        self.ipdtstate = None
        self.prefix = None
        self.mask = None
        self.l3lispiid = None 
        self.l2lispiid = None
        self.isl2only = False
        self.isl3only = False
        self.l3dynstate = False
        self.l3lispdbstate = False
        self.l2dynstate = False
        self.l2lispdbstate = False
        self.l2cps = [] 
        self.l3cps = []
        self.sgt = 0
        self.arpflood = True
        self.multiip = False
        self.rloc = None
        self.mgmtip = None

    def host_onboarding_validation(self, xtr, service):
        self.mgmtip = xtr.mgmtip
        inith =  finddevice(self.mgmtip)
        inith.find_device(service)
        hostname = inith.hostname
        print (hostname)
        #Common conditional to avoid parsing the show command itself and the hostname of the device. Pending to work with other prompts...
        matches = ["#", "show"]

         #Is the source in IPDT
        ipdt_command = "show device-tracking data add {} | i try|/".format(self.sourceip)
        ipdt_output = radkit_cli.get_any_single_output(hostname,ipdt_command,service)

        for line in ipdt_output.splitlines():
            if not any(x  in line for x in matches):
                self.sourcemac = re.compile( "[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}" ).search(line).group().strip()
                self.sourcevlan = re.compile( "(\s([A-Za-z0-9]+\s)+)" ).search(line).group().strip()
                self.sourceport = re.compile( " (?:[A-Z][A-Za-z_-]*[a-z]|[A-Z])\s?\d+(?:\/\d+)*(?::\d+)?(?:\.\d+)? ").search(line).group().strip()
                self.sourceip = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                self.ipdtmethod = re.compile(".*(?= \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})").search(line).group().strip()
           
        if self.sourcemac==None:
            sys.exit("No IPDT Entry for this host!")


        #Retrieve Anycast GW Information
        svi_command = "show ip interface vlan{}".format(self.sourcevlan)
        svi_output = radkit_cli.get_any_single_output(hostname,svi_command,service)

        for line in svi_output.splitlines():
            if "Internet" in line:
                prefixandmask = re.compile( "(?:[0-9]{1,3}[.]){3}[0-9]{1,3}/[0-9]{1,2}" ).search(line).group().strip()
                prefixandmask = prefixandmask.split("/")
                self.prefix=prefixandmask[0]
                self.mask=prefixandmask[1]
            if "Local Proxy" in line:
                if "enabled" in line:
                    localproxyflag=True
                if "disabled" in line:
                    self.isl3only=False
            if "VPN" in line:
                self.sourcevrf= re.compile("\"(.*?)\"").search(line).group().strip("\"")
        if self.prefix=="":
            self.isl2only=True
            print("Subnet is L2Only / L2VNI ")


        #Retrieve LISP Information (L2 or L3)
    
        #l2lisp_iid_output="0"
        #l3lisp_iid_output=" IID 0, "

        #L2 LISP Operations (Local DB, Local EID and DynEID)
        #Find the L2 instance-id
        if self.isl3only==False:
            l2lisp_iid_cmd = "show lisp eid-table vlan {} ethernet | i Instance".format(self.sourcevlan)
            l2lisp_output = radkit_cli.get_any_single_output(hostname,l2lisp_iid_cmd,service)
            for line in l2lisp_output.splitlines():
                if "Instance" in line:
                    self.l2lispiid = re.findall(r'[0-9]+',line)[0]
            
            if self.l2lispiid==0:
                sys.exit("L2 LISP IID Not Found, Is this an L3 Only Subnet?")
            dynl2_cmd = "show lisp instance-id {} dynamic-eid summary | i {}".format(self.l2lispiid, self.sourcemac)
            dynl2_output = radkit_cli.get_any_single_output(hostname,dynl2_cmd,service)
            for line in dynl2_output.splitlines():
                if not any(x  in line for x in matches):
                    if line=="":
                        sys.exit("Source MAC {} in IPDT but not in LISP {} Dynamic-EID, is LISP database-mapping configured for VLAN {}?".format(self.sourcemac,self.l2lispiid,self.sourcevlan))
                    else:
                        self.l2dynstate= True
            dbl2_cmd = "show lisp instance-id {} ethernet database {}".format(self.l2lispiid, self.sourcemac)
            dbl2_output = radkit_cli.get_any_single_output(hostname,dbl2_cmd,service)
            for line in dbl2_output.splitlines():
                if not any(x  in line for x in matches):
                    if "No database-mapping" in line:
                        sys.exit("Source MAC {} in IPDT/ DynEID but not in LISP {} Database? Debug LISP".format(self.sourcemac,self.l2lispiid))
                    else:
                        self.l2lispdbstate = True
            
            l2mr_cmd = "show lisp instance-id {} ethernet | se Map-Resol".format(self.l2lispiid)
            l2mr_op = radkit_cli.get_any_single_output(hostname,l2mr_cmd,service)
            for line in l2mr_op.splitlines():
                if not any(x  in line for x in matches):
                    if '.' in line:
                        msmr = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                        try:
                            self.l2cps.append(msmr)
                        except AttributeError:
                            sys.exit("Source device {} has no Control Planes defined for L2".format(hostname))

            arl2_cmd = "show device-tracking policies vlan {}".format(self.sourcevlan)
            arl2_output = radkit_cli.get_any_single_output(hostname,arl2_cmd,service)
            for line in arl2_output.splitlines():
                if "AR-RELAY" in line:
                    self.arpflood=False
                if "MULTI-IP" in line:
                    self.multiip=True


        #L3 LISP Operations (Local DB, Local EID and DynEID)
        if self.isl2only==False:
            l3lisp_iid_cmd = "show lisp vrf {} | i IID".format(self.sourcevrf)
            l3lisp_output = radkit_cli.get_any_single_output(hostname,l3lisp_iid_cmd,service)
            for line in l3lisp_output.splitlines():
                if "lock" in line:
                    self.l3lispiid = re.compile("(?<=IID).*(?=, l)").search(line).group().strip()
            if self.l3lispiid==0:
                sys.exit("L3 LISP IID Not Found, Is this an L2 Only Subnet?")
            dynl3_cmd = "show lisp instance-id {} dynamic-eid {}".format(self.l3lispiid, self.sourceip)
            dynl3_output = radkit_cli.get_any_single_output(hostname,dynl3_cmd,service)
            for line in dynl3_output.splitlines():
                if not any(x  in line for x in matches):
                    if "No dynamic-EID" in line:
                        sys.exit("Source IP {} in IPDT but not in LISP {} Dynamic-EID, is LISP DynEID configured for {}?".format(self.sourceip,self.l3lispiid,self.prefix))
                    else:
                        self.l3dynstate = True
            dbl3_cmd = "show lisp instance-id {} ipv4 database {}/32".format(self.l3lispiid, self.sourceip)
            dbl3_output = radkit_cli.get_any_single_output(hostname,dbl3_cmd,service)
            for line in dbl3_output.splitlines():
                if not any(x  in line for x in matches):
                    if "No database-mapping" in line:
                        sys.exit("Source IP {} in IPDT/ DynEID but not in LISP {} Database? Debug LISP".format(self.sourceip,self.l3lispiid))
                    else:
                        self.l3lispdbstate = True      
            l3mr_cmd = "show lisp instance-id {} ipv4 | se Map-Resol".format(self.l3lispiid)
            l3mr_op = radkit_cli.get_any_single_output(hostname,l3mr_cmd,service)
            for line in l3mr_op.splitlines():
                if not any(x  in line for x in matches):
                    if '.' in line:
                        msmr = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                        try:
                            self.l3cps.append(msmr)
                        except AttributeError:
                            sys.exit("Source device {} has no Control Planes defined for L3".format(hostname))

        #CTS/SGT assignment
        if self.isl2only==False:
            sgt_cmd = "show ip cef vrf {} {} internal | i SGT".format(self.sourcevrf,self.sourceip)
            sgt_output = radkit_cli.get_any_single_output(hostname,sgt_cmd,service)
            for line in sgt_output.splitlines():
                if "RBAC" in line:
                    self.sourcesgt = re.compile("(?<=SGT).*(?=S)").search(line).group().strip()
        if self.isl2only==True:
            sgt_cmd = "show ip cef {} | i SGT internal".format(self.sourceip)
            sgt_output = radkit_cli.get_any_single_output(hostname,sgt_cmd,service)
            for line in sgt_output.splitlines():
                if "RBAC" in line:
                    self.sourcesgt = re.compile("(?<=SGT).*(?=S)").search(line).group().strip()


        #Loopback verification RLOC, priority, wight and priority and affinity
