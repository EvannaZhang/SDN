"""Example Topology Manager Template
CSCI168False

This class is meant to serve as an example for how you can track the
network's topology from netwokr events.

**You are not required to use this file**: feel free to extend it,
change its structure, or replace it entirely.

"""

from ryu.topology.switches import Port, Switch, Link
# define the maximum value
MAX = float('inf')

class Device:
    """Base class to represent an device in the network.

    Any device (switch or host) has a name (used for debugging only)
    and a set of neighbors.
    """
    def __init__(self, name):
        self.name = name
        # attributes used to compute the shortest path
        self.neighbors = []
        self.checked = False
        self.path = []
        self.distance = MAX

    # used to comparing attributes while adding to heap
    def __lt__(self, other):
        return self.distance < other.distance

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.name)
    

class TMSwitch(Device):
    """Representation of a switch, extends Device

    This class is a wrapper around the Ryu Switch object,
    which contains information about the switch's ports
    """

    def __init__(self, name, switch):
        super(TMSwitch, self).__init__(name)
         
        self.switch = switch
        
        # TODO:  Add more attributes as necessary

    def get_dpid(self):
        """Return switch DPID"""
        return self.switch.dp.id

    def get_ports(self):
        """Return list of Ryu port objects for this switch
        """
        return self.switch.ports

    def get_dp(self):
        """Return switch datapath object"""
        return self.switch.dp

    def delete_neighbor(self, device):
        for relation in self.neighbors:
            if relation[0] is device:
                self.neighbors.remove(relation)
    # . . .


class TMHost(Device):
    """Representation of a host, extends Device

    This class is a wrapper around the Ryu Host object,
    which contains information about the switch port to which
    the host is connected
    """

    def __init__(self, name, host):
        super(TMHost, self).__init__(name)
              
        self.host = host
        # TODO:  Add more attributes as necessary

    def get_mac(self):
        return self.host.mac

    def get_ips(self):
        return self.host.ipv4

    def get_port(self):
        """Return Ryu port object for this host"""
        return self.host.port

    # . . .


class TopoManager:
    """
    Example class for keeping track of the network topology

    """
    def __init__(self):
        # TODO:  Initialize some data structures
        self.all_devices = []
        # to store ip and mac mapping
        self.ip_to_mac = []

    def add_switch(self, sw):
        name = "switch_{}".format(sw.dp.id)
        switch = TMSwitch(name, sw)

        self.all_devices.append(switch)
        # TODO:  Add switch to some data structure(s)

    # to return the specific datapath by id
    def get_switch(self, dpid):
        for i in self.all_devices:
            if self.is_switch(i):
                if i.get_dpid() == dpid:
                    return i.get_dp()

    # check the type of the device
    def is_switch(self, i):
        return isinstance(i, TMSwitch)

    def add_host(self, h):
        name = "host_{}".format(h.mac)
        host = TMHost(name, h)
        self.all_devices.append(host)

        # TODO:  Add host to some data structure(s)
        # after a new host is added, update neighbor information of this host and influenced switch
        for i in self.all_devices:
            if self.is_switch(i):
                if i.name == "switch_{}".format(h.port.dpid):
                    host.neighbors.append((i, None))
                    i.neighbors.append((host, h.port))

    def add_link(self, ev):
        # after a new link is added, update information
        for i in self.all_devices:
            if self.is_switch(i) and i.get_dpid() == ev.link.src.dpid:
                for j in self.all_devices:
                    if self.is_switch(j) and j.get_dpid() == ev.link.dst.dpid:
                        i.neighbors.append((j, ev.link.src))
                        #j.neighbors.append((i, ev.link.dst))

    def delete_host(self, h):
        for i in self.all_devices:
            if not self.is_switch(i):
                if i.name == "host_{}".format(h.mac):
                    for neighbor in i.neighbors:
                        i.delete_neighbor(neighbor)
                    self.all_devices.remove(i)

    def delete_link(self, ev):
        # after a link is deleted, update information
        for i in self.all_devices:
            if self.is_switch(i) and i.get_dpid() == ev.link.src.dpid:
                for j in self.all_devices:
                    if self.is_switch(j) and j.get_dpid() == ev.link.dst.dpid:
                        i.delete_neighbor(j)
                        j.delete_neighbor(i)
    
    def delete_switch(self, sw):
        # after a switch is deleted, remove corresponding information
        for i in self.all_devices:
            if self.is_switch(i):
                if i.name == "switch_{}".format(sw.switch.dp.id):
                    for neighbor in i.neighbors:
                        i.delete_neighbor(neighbor)
                    self.all_devices.remove(i)
    # . . .

