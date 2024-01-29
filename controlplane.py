from dataclasses import dataclass
import radkit_client
import ipaddress
import re
import sys
from device_profiler import device, finddevice
import radkit_cli

class cp_info:

    def __init__(self,eid, qtype):
        self.qtype = qtype  #Types: L3, L2, L2AR
        self.eid = eid      #Can be : IPv4, MAC address (IPv6 not needed for now)
        self.etrs = None    #List of ETRs registering this EID
        self.authenfailures = None #Number of authentication Failures
        self.protocol = None #Was this registered using UDP or TCP?
        self.sitekey = None #What is the Authentication Key for this CP?
        self.cpcpu = None #What is the CPU percentage on this CP?
        self.isfewap = None #Is this EID an AP Radio MAC? True or False
        self.regbywlc = None #Is this EID registered by a WLC? True or False? If so, whats the WLC IP?
        self.domainid = None #Domain ID for this registration
        self.multidomain = None #Multihoming ID for this registration
        self.arbinding = None #What is the IP address of this MAC binding if any?
        self.queriedcp = None #What is the IP address of this queried CP?
