
from dataclasses import dataclass
import radkit_client
import ipaddress
import re
import sys
from device_profiler import device, finddevice
import radkit_cli

def etherchannel_parse(service, intf, device):

    #Returns physical interfaces ONLY in UP state
    matches = ["#", "show"]
    ponumb = re.compile( "\d+" ).search(intf).group().strip()
    #L2 Definition:
    po_cmd = "show etherchannel {} port | i Port:".format(ponumb)
    po_op = radkit_cli.get_any_single_output(device, po_cmd, service)
    pos_cmd ="show etherchannel {} port | i Port state".format(ponumb)
    pos_op = radkit_cli.get_any_single_output(device, pos_cmd, service)
    phy = []
    state = []

    for line in po_op.splitlines():
        if "Port: " in line:
            port = re.compile("(?:[A-Z][A-Za-z_-]*[a-z]|[A-Z])\s?\d+(?:\/\d+)*(?::\d+)?(?:\.\d+)?").search(line).group(0).strip()
            phy.append(port)
    print (pos_op)
    for line in pos_op.splitlines():
        if "state" in line:
            if "Up" in line:
                if "Suspend" in line:
                        state.append ("Suspend")
                elif "Wait" in line:
                        state.append ("Waiting")
                else:
                        state.append("UP")
            if "Down" in line:
                state.append("Down")
    print (phy)
    print (state)
    final = []
    for i,j in zip(phy,state):
        if j == "UP":
            final.append(i)
    return (final)

class cp_eid:

    def __init__(self,eid, iid, queriedcp):
        #self.qtype = qtype  #Types: L3v4, L3v6, L2, L2AR
        self.eid = eid      #Can be : IPv4, MAC address (IPv6 not needed for now)
        self.iid = iid      #LISP Instance ID for the request
        self.etrs = None    #List of ETRs registering this EID
        self.protocol = "UDP" #Was this registered using UDP or TCP?
        self.isfewap = None #Is this EID an AP Radio MAC? True or False
        self.regbywlc = None #Is this EID registered by a WLC? True or False? If so, whats the WLC IP?
        self.domainid = None #Domain ID for this registration
        self.multidomain =  None #Multihoming ID for this registration
        self.arbinding = None #What is the MAC address of this IP binding if any?
        self.queriedcp = queriedcp #What is the IP address of this queried CP?

    #Layer 2 (MAC) Control Plane Query
    def ethernet_q(self, service):
        etr_list = []
        cmd = "sh lisp instance-id {} ethernet server {}".format(self.iid, self.eid)
        cp_server_output = radkit_cli.get_any_single_output(self.queriedcp,cmd,service)
        self.arbinding = "NA"

        if cp_server_output == None:
            sys.exit("MAC Address not found in control plane")

        for line in cp_server_output.splitlines():
            if "ETR" in line:
                etrs = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                etr_list.append(etrs) 

            if "sourced by reliable transport" in line:
                    self.protocol = "TCP"

            if "Domain-ID" in line:
                try:
                    self.domainid = re.compile( "\d+" ).search(line).group().strip()
                except:
                    self.domainid = "unspecified"
            if "Multihoming-ID" in line:
                try:
                    self.multidomain = re.compile( "\d+" ).search(line).group().strip()
                except:
                    self.multidomain = "unspecified"

            if "WLC AP bit:" in line:
                self.regbywlc = "True" 
                if "Set" in line:
                    self.isfewap = "True"
                if "Clear" in line:
                    self.isfewap = "False"
        
        self.etrs = etr_list

    #Layer 3 (IPv4) Control Plane Query
    def layer3_q(self, service):
            etr_list = []
            cmd = "sh lisp instance-id {} ipv4 server {}".format(self.iid, self.eid)
            cp_server_output = radkit_cli.get_any_single_output(self.queriedcp,cmd,service)
            self.isfewap = "NA"
            self.regbywlc = "NA"

            if cp_server_output == None:
                sys.exit("IP is not found in control plane")

            for line in cp_server_output.splitlines():
                if "ETR" in line:
                    etrs = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                    etr_list.append(etrs)

                if "sourced by reliable transport" in line:
                    self.protocol = "TCP"
                
                if "Domain-ID" in line:
                    try:
                        self.domainid = re.compile( "\d+" ).search(line).group().strip()
                    except:
                        self.domainid = "unspecified"
                if "Multihoming-ID" in line:
                    try:
                        self.multidomain = re.compile( "\d+" ).search(line).group().strip()
                    except:
                        self.multidomain = "unspecified"   
            self.etrs = etr_list

    #Layer 2 (Address Resolution) Control Plane Query
    def addres_q(self, service):
            etr_list = []
            cmd = "sh lisp instance-id {} ethernet server address-resolution {}".format(self.iid, self.eid)
            cp_server_output = radkit_cli.get_any_single_output(self.queriedcp,cmd,service)
            #Address resolution is always registered using TCP
            self.protocol = "TCP"
            self.domainid = "NA"
            self.multidomain = "NA" 
            self.isfewap = "NA"
            self.regbywlc = "NA"

            if cp_server_output == None:
                sys.exit("ARP is not found in control plane")

            for line in cp_server_output.splitlines():
                if "ETR" in line:
                    etrs = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group().strip()
                    etr_list.append(etrs)
            
                if "Hardware" in line:
                    self.arbinding = re.compile("[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}").search(line).group().strip()       
            self.etrs = etr_list

class cp_state:

    def __init__(self,etr,eid, iid, queriedcp):
        self.eid = eid      #Can be : IPv4, MAC address (IPv6 not needed for now)
        self.iid = iid      #LISP Instance ID for the request
        self.etr = etr      #Loopback0 of the device that should be registering X endpoint
        self.ttl = None #What is the TTL of this registration?
        self.authenfailures = None #Number of authentication Failures
        #self.sitekey = None #What is the Authentication Key for this CP?
        self.lispsessionstate = None #What is the status of the LISP session? (WLCs can have more than 1 session)
        self.lispsessionmtu = None #What is the value of the MTU for this session?
        self.retransmitcounter = None #How many retransmissions are being observed for this LISP session?
        self.cpcpu = None #What is the CPU percentage on this CP?
        self.queriedcp = queriedcp #What is the IP address of this queried CP?

    def session_state(self,service):
        #CPU Utilization
        cpu_cmd = "show process cpu sorted | i utili"
        cpu_output = radkit_cli.get_any_single_output(self.queriedcp,cpu_cmd,service)
        for line in cpu_output.splitlines():
            if "minute" in line:
                self.cpcpu = re.compile( "\d+(?:\\.\\d+)?%" ).search(line).group().strip()

        #LISP Session Parser
        ls_cmd = "show lisp session all | i {}".format(self.etr)
        lisp_session_output = radkit_cli.get_any_single_output(self.queriedcp,ls_cmd,service)

        for line in lisp_session_output.splitlines():
            if "Up" in line:
                self.lispsessionstate = "UP"
                tcpcmd = "show tcp brief numeric | i {}".format(self.etr)
                tcpoutput = radkit_cli.get_any_single_output(self.queriedcp,tcpcmd,service)
                for line in tcpoutput.splitlines():
                    if "4342" in line:
                        tcb = re.compile( "([^\s]+)" ).search(line).group(0).strip()
                        tcbcmd = "show tcp tcb {}".format(tcb)
                        tcboutput = radkit_cli.get_any_single_output(self.queriedcp,tcbcmd,service)
                        for line in tcboutput.splitlines():
                            if "MSS" in line:
                                self.lispsessionmtu = re.compile( "\d+" ).search(line).group().strip()
                            if "partialack" in line:
                                self.retransmitcounter = re.compile("(?<=retransmit:).*(?=, f)").search(line).group().strip()
            if "NoRoute" in line:
                self.lispsessionstate = "No Route"
                sys.exit("LISP Session to ETR {} is Down because of missing underlay route!".format(self.etr))
            if "Down" in line:
                self.lispsessionstate = "Down"
                tcpcmd = "show tcp brief numeric | i {}".format(self.etr)
                tcpoutput = radkit_cli.get_any_single_output(self.queriedcp,tcpcmd,service)
                for line in tcpoutput.splitlines():
                    if "4342" in line:
                        tcb = re.compile( "([^\s]+)" ).search(line).group(0).strip()
                        tcbcmd = "show tcp tcb {}".format(tcb)
                        tcboutput = radkit_cli.get_any_single_output(self.queriedcp,tcbcmd,service)
                        for line in tcboutput.splitlines():
                            if "MSS" in line:
                                self.lispsessionmtu = re.compile( "\d+" ).search(line).group().strip()
                            if "partialack" in line:
                                self.retransmitcounter = re.compile("(?<=retransmit:).*(?=, f)").search(line).group().strip()
                sys.exit("LISP Session to ETR {} is Down".format(self.etr))
        if self.lispsessionstate == None:
            sys.exit("LISP Session to ETR {} is Down or Not Found!".format(self.etr))

        #Keys cannot be gathered via radkit, they show xxxxxxxx
        #authcmd = "sh run | i authentication-key"
        #auth_server_output = radkit_cli.get_any_single_output(self.queriedcp,authcmd,service)
        #for line in auth_server_output.splitlines():    
        #    line = line.replace(" ","")
        #    try:
        #        self.sitekey = re.compile ("(?<=^authentication-key[0-9]).*").search(line).group().strip()
        #    except:
        #        pass


    def l2_state(self, service):

        cmd = "show lisp instance-id {} ethernet server {}".format(self.iid, self.eid)
        cp_server_output = radkit_cli.get_any_single_output(self.queriedcp,cmd,service)

        if cp_server_output == None:
            sys.exit("MAC is not found in control plane")
        for line in cp_server_output.splitlines():
            if "TTL:" in line:
                self.ttl = re.compile( "(?<=:).*" ).search(line).group().strip()
            if "failures" in line:
                self.authenfailures = re.compile("\d+").search(line).group().strip()
        self.session_state(service)

    def l3_state(self, service):

        cmd = "show lisp instance-id {} ipv4 server {}".format(self.iid, self.eid)
        cp_server_output = radkit_cli.get_any_single_output(self.queriedcp,cmd,service)

        if cp_server_output == None:
            sys.exit("MAC is not found in control plane")
        for line in cp_server_output.splitlines():
            if "TTL:" in line:
                self.ttl = re.compile( "(?<=:).*" ).search(line).group().strip()
            if "failures" in line:
                self.authenfailures = re.compile("\d+").search(line).group().strip()
        self.session_state(service)

class cp_etr_state:
#Validation of Control Plane from the ETR perspective
    def __init__(self,queriedcpip, queriedetr):
            #self.mskey = None #What is the Authentication Key for this CP, this value is hidden!
            self.lispsessionstate = None #What is the status of the LISP session? (WLCs can have more than 1 session)
            self.lispsessionmtu = None #What is the value of the MTU for this session?
            self.retransmitcounter = None #How many retransmissions are being observed for this LISP session?
            self.queriedcp = queriedcpip
            self.cproute = None #Is there a route to the CP?
            self.queriedetr = queriedetr 
        
    def route_parser(self, service):
        rib_cmd = "show ip route {}".format(self.queriedcp)
        rib_op = radkit_cli.get_any_single_output(self.queriedetr,rib_cmd,service)
        if rib_op != None:
            for line in rib_op.splitlines():
                if "entry" in line:
                    prefix = re.compile("(?<=for ).*()").search(line).group().strip()
                    prefix = prefix.split("/")
                    pfx = prefix[0]
                    mask = prefix[1]
                if "Known" in line:
                    prc = re.compile("(?<=Known via).*(?=, d)").search(line).group().strip()
                    prc = prc.strip("\"")
            route = {'Prefix' : pfx, 'Mask' : mask, 'Protocol' : prc}
            if pfx != None:
                self.cproute = route
        if rib_op == None:
            rib_cmd = "show ip route 0.0.0.0"
            rib_op = radkit_cli.get_any_single_output(self.queriedetr,rib_cmd,service)
            for line in rib_op.splitlines():
                if "Known" in line:
                    prc = re.compile("(?<=Known via).*(?=, d)").search(line).group().strip()
                    prc = prc.strip("\"")
                    route = {'Prefix' : "0.0.0.0", 'Mask' : "0", 'Protocol' : prc }
            if prc == None:
                route = {'Prefix' : "No Route" }
            self.cproute = route
                

    def session_state(self,service):
        #CPU Utilization

        #LISP Session Parser
        ls_cmd = "show lisp session all | i {}".format(self.queriedcp)
        lisp_session_output = radkit_cli.get_any_single_output(self.queriedetr,ls_cmd,service)

        for line in lisp_session_output.splitlines():
            if "Up" in line:
                self.lispsessionstate = "UP"
                tcpcmd = "show tcp brief numeric | i {}".format(self.queriedcp)
                tcpoutput = radkit_cli.get_any_single_output(self.queriedetr,tcpcmd,service)
                for line in tcpoutput.splitlines():
                    if "4342" in line:
                        tcb = re.compile( "([^\s]+)" ).search(line).group(0).strip()
                        tcbcmd = "show tcp tcb {}".format(tcb)
                        tcboutput = radkit_cli.get_any_single_output(self.queriedetr,tcbcmd,service)
                        for line in tcboutput.splitlines():
                            if "MSS" in line:
                                self.lispsessionmtu = re.compile( "\d+" ).search(line).group().strip()
                            if "partialack" in line:
                                self.retransmitcounter = re.compile("(?<=retransmit:).*(?=, f)").search(line).group().strip()
            if "NoRoute" in line:
                self.lispsessionstate = "No Route"
                self.route_parser(service)
                print ("LISP Session to CP {} is Down because of missing underlay route!".format(self.queriedcp))
            if "Down" in line:
                self.lispsessionstate = "Down"
                tcpcmd = "show tcp brief numeric | i {}".format(self.queriedcp)
                tcpoutput = radkit_cli.get_any_single_output(self.queriedcp,tcpcmd,service)
                for line in tcpoutput.splitlines():
                    if "4342" in line:
                        tcb = re.compile( "([^\s]+)" ).search(line).group(0).strip()
                        tcbcmd = "show tcp tcb {}".format(tcb)
                        tcboutput = radkit_cli.get_any_single_output(self.queriedetr,tcbcmd,service)
                        for line in tcboutput.splitlines():
                            if "MSS" in line:
                                self.lispsessionmtu = re.compile( "\d+" ).search(line).group().strip()
                            if "partialack" in line:
                                self.retransmitcounter = re.compile("(?<=retransmit:).*(?=, f)").search(line).group().strip()
                print ("LISP Session to CP {} is Down".format(self.etr))
        if self.lispsessionstate == None:
            self.route_parser(service)
            print("LISP Session to CP {} is Down or Not Found!".format(self.queriedcp))
        
        self.route_parser(service)

        #Keys cannot be gathered via radkit, they show xxxxxxxx
        #authcmd = "sh run | i authentication-key"
        #auth_server_output = radkit_cli.get_any_single_output(self.queriedcp,authcmd,service)
        #for line in auth_server_output.splitlines():    
        #    line = line.replace(" ","")
        #    try:
        #        self.sitekey = re.compile ("(?<=^authentication-key[0-9]).*").search(line).group().strip()
        #    except:
        #        pass

class l2_map_cache:

    def __init__(self,eid, iid, mctype):
        self.qtype = mctype         #Types: ipv4, ipv6 or ethernet
        self.eid = eid              #Can be : IPv4, MAC address (IPv6 not needed for now)
        self.iid = iid              #LISP Instance ID for the request
        self.mask = None            #Mask of the EID, MAC addresses are /48 always
        self.uptime = None          #Uptime of the map-cache
        self.expiration = None      #Expiration 
        self.source = None          #Via which method? Map-reply? Static? Publication?  
        self.rloc = None            #RLOC IP
        self.rlocstate = None       #What is the state, up, route-reject, admin-down, no-route? self?, list of RLOCs, dict
        self.priority = None        #LISP priority
        self.weight = None          #LISP weight
        self.encapiid = None        #For LISP Extranet 

class l3_map_cache:

    def __init__(self,eid, iid, mctype):
        self.qtype = mctype         #Types: ipv4, ipv6 or ethernet
        self.eid = eid              #Can be : IPv4, MAC address (IPv6 not needed for now)
        self.iid = iid              #LISP Instance ID for the request
        self.mask = None            #Mask for the EID
        self.uptime = None          #Uptime of the map-cache
        self.expiration = None      #Expiration 
        self.source = None          #Via which method? Map-reply? Static? Publication?  
        self.nmr = None             #Is it NMR? True or False
        self.petr = None            #Is it sending to PETR? which PETRs? List of PETR and its states
        self.domainid = None        #DomainID
        self.mhid = None            #Multihoming ID
        self.rloc = None            #RLOC IP
        self.rlocstate = None       #What is the state, up, route-reject, admin-down, no-route? self?, list of RLOCs, dict
        self.priority = None        #LISP priority
        self.weight = None          #LISP weight
        self.encapiid = None        #For LISP Extranet 

class route_recursion:
    def __init__(self,route,device):
        self.device = device        #Device Name
        self.route = route            #IPv4 RLOC 
        self.criteria = None        #Exclude default, min /32 or min/32 proxy-etr-only
        self.prefix = None          #Prefix covering this RLOC in global RIB 
        self.mask = None            #Mask covering this prefix
        self.protocol = None        #Route IGP/EGP
        self.nexthop = None         #Next Hop(s) covering this prefix
        self.phy = None             #List of interfaces recursing this next hop 
        self.mtu = None             #MTU of physical interfaces
        self.ping_to_rloc = None    #Validation of RLOC-to-RLOC reachability
        self.mtu_validation = None  #MTU validation


    def rloc_data(self,service):

        devbulk = service.inventory[self.device]
        
        rib_cmd = "show ip route {}".format(self.route)
        reach_cmd = "show run | i tor reach"
        cef_cmd = "show ip cef {}".format(self.route)
        ping_cmd = "ping {} source lo0 time 1".format(self.route)

        print("Obtaining Routing information for {}".format(self.route))

        try:
            commands1 = devbulk.exec([rib_cmd,reach_cmd,cef_cmd,ping_cmd]).wait()
        except (IndexError, ValueError):
            sys.exit("Unable to fetch configuration from device {}".format(self.device))  
        

        rib_op = commands1.result["{}".format(rib_cmd)].data
        cef_op = commands1.result["{}".format(cef_cmd)].data
        reach_op = commands1.result["{}".format(reach_cmd)].data
        ping_op = commands1.result["{}".format(ping_cmd)].data

        #RLOC Reachability
        print("Determining Reachability Criteria")
        for line in reach_op.splitlines():
            
            if "ipv4" in line:
                if "minimum-mask" in line:
                    if "proxy-etr" in line:
                        self.criteria = "MM-PETR"
                    else: 
                        self.criteria = "MM"
                if "exclude" in line:
                    self.criteria = "ED"

        #Route_Inspection:
        print("Processing RIB Information")
        if rib_op != None:
            nh = []
            for line in rib_op.splitlines():
                if "entry" in line:
                    prefix = re.compile("(?<=for ).*()").search(line).group().strip()
                    prefix = prefix.split("/")
                    self.prefix = prefix[0]
                    self.mask = prefix[1]
                if "Known" in line:
                    prc = re.compile("(?<=Known via).*(?=, d)").search(line).group().strip()
                    self.protocol = prc.strip("\"")
                if ", via" in line:
                    nhop = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group(0).strip()
                    nh.append(nhop)
            self.nexthop = nh

        if rib_op == None:
            nh = []
            rib_cmd = "show ip route 0.0.0.0"
            rib_op = radkit_cli.get_any_single_output(self.queriedetr,rib_cmd,service)
            for line in rib_op.splitlines():
                if "Known" in line:
                    prc = re.compile("(?<=Known via).*(?=, d)").search(line).group().strip()
                    self.protocol = prc.strip("\"")
                    self.prefix = "0.0.0.0"
                    self.mask = "0"
                if ", via" in line:
                    nhop = re.compile( "(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" ).search(line).group(0).strip()
                    nh.append(nhop)
            self.nexthop = nh
            if prc == None:
                sys.exit("No Route to RLOC! Traffic wil l be Dropped")
            
        #PHY Indentification
            
        #Current state supports the following Next Hop parsing form CEF: L3 Port-Channel, SVI and Physical.
        #Support for Tunnel, Apphosting, VTI, LISP and NVE interfaces is not yet considered...

        print("Calculating Physical Interfaces")
        phys = []
        matches = ["#", "show"]
        for line in cef_op.splitlines():
            if "nexthop " in line:
                #Layer 3 Port-Channel as next hop
                if "channel" in line:
                    phy = re.compile("(?:[A-Z][A-Za-z_-]*[a-z]|[A-Z])\s?\d+(?:\/\d+)*(?::\d+)?(?:\.\d+)?").search(line).group(0).strip()
                    po_phy = etherchannel_parse(service,phy,self.device)
                    for i in po_phy:
                        phys.append(i)
                #SVI as next as hop
                elif "Vlan" in line:
                    nh = re.compile("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})").search(line).group().strip()
                    arp = "show ip arp {}".format(nh)
                    try:
                        arp_op = radkit_cli.get_any_single_output(self.device,arp,service)
                    except:
                        sys.exit("ARP Is Incomplete for next hop {}".format(nh))
                    for line in arp_op.splitlines():
                        if "ARPA" in line:
                            mac = re.compile( "[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}" ).search(line).group().strip()
                            maccmd = "show mac address | i {}".format(mac)
                            try:
                                mac_op = radkit_cli.get_any_single_output(self.device,maccmd,service)
                            except:
                                sys.exit("MAC not learned for ARP {}".format(nh))
                    for line in mac_op.splitlines():
                        if not any(x  in line for x in matches):
                            phy = re.compile("(?:[A-Z][A-Za-z_-]*[a-z]|[A-Z])\s?\d+(?:\/\d+)*(?::\d+)?(?:\.\d+)?").search(line).group(0).strip()
                            if "Po" in phy:
                                po_phy = etherchannel_parse(service,phy,self.device)
                                for i in po_phy:
                                    phys.append(i)
                #Physical Interfaces 
                else:
                    phy = re.compile("(?:[A-Z][A-Za-z_-]*[a-z]|[A-Z])\s?\d+(?:\/\d+)*(?::\d+)?(?:\.\d+)?").search(line).group().strip()
                    if "." in phy:
                        subint = phy.split(("."))
                        phy = subint[0]
                    phys.append(phy)
        self.phy = phys
        if self.phy == "None":
            sys.exit("Unable to find the outgoing physical interfaces for prefix {}, confirm the outgoing interface on the device itself.".format(self.route))

        #MTU validation:

        mtus = []
        for i in phys:
            mtu_cmd = "show interface {} | i MTU".format(i)
            mtu_op = radkit_cli.get_any_single_output(self.device, mtu_cmd, service)
            for line in mtu_op.splitlines():
                if "bytes" in line:
                    mtu = re.compile("(?<=MTU).*(?=bytes)").search(line).group().strip()
                    mtu = int(mtu)
                    mtus.append(mtu)
        mtus.sort()
        mini = mtus[0]

        print ("Testing RLOC-to-RLOC reachability with MTU size of {}".format(mini))
        #Ping with and without MTU size
        pingm_cmd = "ping {} source lo0 time 1 size {} df-bit".format(self.route, mini)
        pingm_op = radkit_cli.get_any_single_output(self.device,pingm_cmd,service)

        #Ping Validation

        for line in ping_op.splitlines():
            if "Success" in line:
                percent = re.compile("(?<=is).*(?=percent)").search(line).group().strip()
                self.ping_to_rloc = percent+"%"
        for line in pingm_op.splitlines():
            if "Success" in line:
                percent = re.compile("(?<=is).*(?=percent)").search(line).group().strip()
                self.mtu_validation = ["{} %".format(percent), "MTU {}".format(mini)]

class underlay_validations:
    def __init__(self,intf,devicename):
        self.device = devicename
        self.intfname = intf 
        self.outputdrops = None
        self.iqdrops = None
        self.txload = None 
        self.rxload = None
        self.crcs = None
        self.giants = None 
        self.inputpps = None 
        self.outputpps = None
    
    def intf_parse(self, service):
        intf_cmd = "show interface {}".format(self.intfname)
        intf_op = radkit_cli.get_any_single_output(self.device,intf_cmd,service)

        for line in intf_op.splitlines():
            if "output drops" in line:
                self.outputdrops = re.compile("(?<=drops:).*").search(line).group().strip()
                iqdrops = re.compile("[\/]\d+[\/]\d+").search(line).group().strip()
                iqdrops = iqdrops.split("/")
                self.iqdrops = iqdrops[2]
            if "tx" in line:
                self.txload = re.compile("(?<=txload).*(?=,)").search(line).group().strip()
                self.rxload = re.compile("(?<=rxload).*(?=)").search(line).group().strip()
            if "CRC" in line:
                self.crcs = re.compile("(?<=,).*(?=CRC)").search(line).group().strip()
            if "giants" in line:
                self.giants = re.compile("(?<=,).*(?=giants)").search(line).group().strip()
            if "t rate" in line:
                if "input" in line:
                    try:
                        self.inputpps = re.compile("(?<=,).*(?=packet)").search(line).group().strip()
                    except:
                        pass
                if "output" in line:
                    try:
                        self.outputpps = re.compile("(?<=,).*(?=packet)").search(line).group().strip()
                    except:
                        pass               

class neighbor_discovery:
    #Optional discovery, as it requires CDP...
    def __init__(self,underlayinfo, sourceinfo, device_list):
        self.sourceinterfaces = None
        self.nhinterafces = None 
        self.nhdevice = None 
