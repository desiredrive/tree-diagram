from dataclasses import dataclass
import radkit_client
import ipaddress
import re
import sys
import ipverifications

#Defining Class for ANY Fabric Device.
class device:

    def __init__(self,mgmtip):
        self.hostname = None
        self.loopback = None
        self.mask = None
        self.edge = False
        self.iborder = False
        self.eborder = False
        self.cp = False
        self.intnode = False
        self.model = None
        self.version = None 
        self.mgmtip = mgmtip
        self.cdpneighbors = None
        self.rlocdef = None

        

    def find_device(self, service):
            
           
            #find device in inventory list
            try:
                self.device_inventory = service.inventory.filter('host', '^{}$'.format(self.mgmtip))
                device_name = list(self.device_inventory.keys())

                #validate
                
                self.hostname = device_name[0]
                self.device_inventory = service.inventory[self.hostname]
                return (self.hostname)

                #Does not exist  
            except (IndexError, ValueError):
                sys.exit("Device {} not in RADKIT inventory".format(self.mgmtip))  

    def profile_device(self, service):
        device.find_device(self,service)

        #Define main IOS Commands
        cmd1 = 'show ip interface loopback0 | i Internet|line'
        cmd2 = 'show version | i ptime'
        cmd3 = 'show lisp service ipv4 | i PITR|Map-Server|Map-Resolver|ETR'
        cmd4 = 'show ip protocols | i lisp'
        cmd5 = 'show run | i route-import'
        cmd6 = 'show run | i tracking tracking'
        cmd7 = 'show lisp service ipv4 | se Map-Server'
        cmd8 = 'show ver | i IOS Soft|bytes of memory'
        cmd9 = 'show cdp neighbor detail | i Device ID|Interface'
        cmd10 = 'show run | i IPv4-interface|affinity'

        try:
            commands1 = self.device_inventory.exec([cmd1,cmd2,cmd3,cmd4]).wait()
            commands2 = self.device_inventory.exec([cmd5,cmd6,cmd7,cmd8]).wait()
            cdp = self.device_inventory.exec([cmd9]).wait()
            loopdef = self.device_inventory.exec([cmd10]).wait()
        except (IndexError, ValueError):
            sys.exit("Unable to fetch configuration from device {}".format(self.mgmtip))  
        
        lo0 = commands1.result["{}".format(cmd1)].data
        fabric_role = commands1.result["{}".format(cmd3)].data
        lisp_enabled = commands1.result["{}".format(cmd4)].data
        internal_border = commands2.result["{}".format(cmd5)].data
        fe_ipdtcheck = commands2.result["{}".format(cmd6)].data
        map_servers = commands2.result["{}".format(cmd7)].data
        model_ios = commands2.result ["{}".format(cmd8)].data
        cdpneiop = cdp.result["{}".format(cmd9)].data
        loopres = loopdef.result["{}".format(cmd10)].data
    
        for line in lo0.splitlines():
            if "line protocol is down" in line: 
                sys.exit("Loopback0 is down at device: {} , unshut the interface".format(self.mgmtip))
            if "Invalid input" in line:
                sys.exit("Loopback 0 does not exist in {} verify the underlay configuration".format(self.mgmtip))
            if "Internet address" in line:
                loopback_address=re.compile( "(?<=address is).*(?=/)" ).search(line).group().strip()
                self.loopback = loopback_address
                mask = re.compile( "(?<=/).*(?=)" ).search(line).group()
                self.mask=mask

        for line in fabric_role.splitlines():
            #PITR Validation
            if "Proxy-ITR Router" in line:
                 pitr = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                 if pitr!=loopback_address:
                      print ("PITR address is not the same as Loopback0, correct this configuration")
                      break
            #PETR Validation
            if "Proxy-ETR Router" in line:
                if "enabled" in line:
                        self.eborder=True
            #CP Validation

        mr_ip = ''
        for line in map_servers.splitlines():
            if '.' in line:
                mr_ip = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                if mr_ip==loopback_address:
                    self.cp=True
            
        #LISP Validation
        for line in lisp_enabled.splitlines():
            if "Routing Protocol is" in line:
                self.intnode=False

        #Internal Border Validation
        for line in internal_border.splitlines():
            if "route-import database bgp" in line:
                self.iborder=True

        #Edge node Validation (or L2 Border...)
        for line in fe_ipdtcheck.splitlines():
            if "device-tracking tracking" in line:
                self.edge=True
    
        #IOS and Model
        for line in model_ios.splitlines():
            if "Cisco IOS" in line:
                IOSversion = re.compile( "(?<=Version).*(?=\[)|(?<=Version)(.*)(?=, REL)" ).search(line).group().strip()
                self.version=IOSversion
            if "processor" in line:
                model = re.compile( "(?<=cisco ).*(?=.\(.*proces)" ).search(line).group().strip()
                self.model=model

        #CDP Neighbors
        matches = ["#", "show"]
        neighbors = []
        rmtintfs = []
        localintfs = []
        cdpneis = {}

        for line in cdpneiop.splitlines():
            if not any(x  in line for x in matches):
                if "Device ID:" in line:
                    neighbor = re.compile("(?<=ID:).*(?=)?").search(line).group().strip()
                    neighbors.append(neighbor)

                if "outgoing port" in line:
                    rmtintf = re.compile("(?<=port\):).*(?=)?").search(line).group().strip()
                    rmtintfs.append(rmtintf)
                    localintf = re.compile("(?<=face:).*(?=,)").search(line).group().strip()
                    localintfs .append(localintf)

        cdpointer = 0
        for i,j,k in zip(neighbors,localintfs,rmtintfs):
            if j != "GigabitEthernet0/0":
                cdpneis[cdpointer] = {'Name' : i, 'Local Intf' : j, 'Remote Intf' : k}
                cdpointer+=1
        self.cdpneighbors = cdpneis


          #Loopback verification RLOC, priority, weight and priority and affinity

        if self.edge == True or self.iborder == True or self.eborder == True:
            valoop = {'Interface': '', 'Priority' : '', 'Weight' : '', 'Affinity' : ''}
            priority = ''
            weight = ''
            affinity = []
            loopbackstate = False
            for line in loopres.splitlines():
                if "IPv4-interface Loopback0" in line:
                    loopbackstate = True
                    if "priority" in line:
                        priority = re.compile("(?<=priority\s)[0-9]+").search(line).group().strip()
                    if "weight" in line:
                        weight = re.compile("(?<=weight\s)[0-9]+").search(line).group().strip()                        
                    if "affinity-id" in line:
                        aff = re.compile("(?<=affinity-id\s)[0-9]+").search(line).group().strip()
                        affinity.append(aff)
                        aff = re.compile("(?<=,\s)[0-9]+").search(line).group().strip()
                        affinity.append(aff)
                        print (loopres.splitlines())

            if loopbackstate == False:
                 print("RLOC Interface Not Found, Verify if the Loopback0 is being used as RLOC.")
                 interface = None
            if loopbackstate == True:
                 interface = "Lo0"
            valoop = {'Interface': interface, 'Priority' : priority, 'Weight' : weight, 'Affinity' : affinity}
            self.rlocdef = valoop  

        elif self.cp == True and (self.iborder==False or self.eborder==False):
            print("This device is a dedicated CP")

        
            


class finddevice:
    def __init__(self,mgmtip):
        self.mgmtip = mgmtip
    def find_device(self, service):
           
            #find device in inventory list
            try:
                self.device_inventory = service.inventory.filter('host', '^{}$'.format(self.mgmtip))
                device_name = list(self.device_inventory.keys())

                #validate
                
                self.hostname = device_name[0]
                self.device_inventory = service.inventory[self.hostname]
                return (self.hostname)

                #Does not exist  
            except (IndexError, ValueError):
                sys.exit("Device {} not in RADKIT inventory".format(self.mgmtip))  


#FabricSite based on management SUBNET/LANAUTO, all devices in the fabric must share a common subnet...
def fabric_builder(subnet,service):
    print ("Getting Loopback information from all fabric devices in the specified subnets, this might take some minutes...")
    fabric_list = {}
    fabric_pointer = 0
    matches = ["IOS"]
    #matches = ["IOS", "AireOS"]
    for currentsubnet in subnet:
        for i in service.inventory:
            name = service.inventory[i]
            ip = name.host
            validate = ipverifications.inside_subnet(currentsubnet, ip)
            if validate == True:
                type = service.inventory[i].device_type
                if any(x == type for x in matches):
                    print ("Profiling {} ...".format(i))
                    loopback0 = get_loopback(i, service)
                    fabric_list[fabric_pointer] = {'Name' : i, 'Host' : ip, 'Type' : type  , 'Loopback0' : loopback0}
                    fabric_pointer+=1
    return (fabric_list)
    

def get_loopback(hostname, service):
    device_inventory = service.inventory[hostname]
    cmd1 = 'show ip interface brief | i Loopback0   '
    try: 
        commands1 = device_inventory.exec([cmd1]).wait()
    except (IndexError, ValueError):
           print ("Unable to fetch configuration from device {}".format(hostname))
    try:
        lo0 = commands1.result["{}".format(cmd1)].data
        for line in lo0.splitlines():
            if "YES" in line:
                loopback_address=re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                return (loopback_address)
    except:
        pass
    
    
