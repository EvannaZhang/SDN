#!/usr/bin/env python3

"""Shortest Path Switching template
CSCI1680

This example creates a simple controller application that watches for
topology events.  You can use this framework to collect information
about the network topology and install rules to implement shortest
path switching.

"""
import queue
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0

from ryu.topology import event, switches
import ryu.topology.api as topo

from ryu.lib.packet import packet, ether_types
from ryu.lib.packet import ethernet, arp, icmp

from ofctl_utils import OfCtl, VLANID_NONE

from topo_manager_example import TopoManager, TMHost, TMSwitch

# define the maximum value
MAX = float('inf')


class ShortestPathSwitching(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ShortestPathSwitching, self).__init__(*args, **kwargs)
        self.tm = TopoManager()

    @set_ev_cls(event.EventSwitchEnter)
    def handle_switch_add(self, ev):
        """
        Event handler indicating a switch has come online.
        """
        switch = ev.switch
        self.logger.warn("Added Switch switch%d with ports:", switch.dp.id)
        for port in switch.ports:
            self.logger.warn("\t%d:  %s", port.port_no, port.hw_addr)

        # TODO:  Update network topology and flow rules
        self.tm.add_switch(switch)
        self.flowtable_update()

    @set_ev_cls(event.EventSwitchLeave)
    def handle_switch_delete(self, ev):
        """
        Event handler indicating a switch has been removed
        """
        switch = ev.switch

        self.logger.warn("Removed Switch switch%d with ports:", switch.dp.id)
        for port in switch.ports:
            self.logger.warn("\t%d:  %s", port.port_no, port.hw_addr)

        # TODO:  Update network topology and flow rules
        self.tm.delete_switch(ev)
        self.flowtable_update()

    @set_ev_cls(event.EventHostDelete)
    def handle_host_delete(self, ev):
        """
        Event handler indicating when a host has been deleted
        """
        host = ev.host

        self.logger.warn("Host Deleted:  %s (IPs:  %s) on switch%s/%s (%s)",
                         host.mac, host.ipv4,
                         host.port.dpid, host.port.port_no, host.port.hw_addr)

        # TODO:  Update network topology and flow rules
        self.tm.delete_host(ev)
        self.flowtable_update()

    @set_ev_cls(event.EventHostAdd)
    def handle_host_add(self, ev):
        """
        Event handler indiciating a host has joined the network
        This handler is automatically triggered when a host sends an ARP response.
        """
        host = ev.host
        self.logger.warn("Host Added:  %s (IPs:  %s) on switch%s/%s (%s)",
                         host.mac, host.ipv4,
                         host.port.dpid, host.port.port_no, host.port.hw_addr)

        # TODO:  Update network topology and flow rules
        self.tm.add_host(host)
        self.flowtable_update()

        # store the ip to mac information to the topo manager
        # find record first, if found, update it
        # if not found, add an entry
        found = False
        for entry in self.tm.ip_to_mac:
            if entry[1] == host.mac:
                entry[0] = host.ipv4[0]
                found = True
            break
        if not found:
            self.tm.ip_to_mac.append([host.ipv4[0], host.mac])

    @set_ev_cls(event.EventLinkAdd)
    def handle_link_add(self, ev):
        """
        Event handler indicating a link between two switches has been added
        """
        link = ev.link
        print(link)
        src_port = ev.link.src
        dst_port = ev.link.dst
        self.logger.warn("Added Link:  switch%s/%s (%s) -> switch%s/%s (%s)",
                         src_port.dpid, src_port.port_no, src_port.hw_addr,
                         dst_port.dpid, dst_port.port_no, dst_port.hw_addr)

        # TODO:  Update network topology and flow rules
        self.tm.add_link(ev)
        self.flowtable_update()

    @set_ev_cls(event.EventLinkDelete)
    def handle_link_delete(self, ev):
        """
        Event handler indicating when a link between two switches has been deleted
        """
        link = ev.link
        src_port = link.src
        dst_port = link.dst

        self.logger.warn("Deleted Link:  switch%s/%s (%s) -> switch%s/%s (%s)",
                         src_port.dpid, src_port.port_no, src_port.hw_addr,
                         dst_port.dpid, dst_port.port_no, dst_port.hw_addr)

        # TODO:  Update network topology and flow rules
        self.tm.delete_link(ev)
        self.flowtable_update()

    @set_ev_cls(event.EventPortModify)
    def handle_port_modify(self, ev):
        """
        Event handler for when any switch port changes state.
        This includes links for hosts as well as links between switches.
        """
        port = ev.port
        self.logger.warn("Port Changed:  switch%s/%s (%s):  %s",
                         port.dpid, port.port_no, port.hw_addr,
                         "UP" if port.is_live() else "DOWN")

        # TODO:  Update network topology and flow rules
        self.flowtable_update()

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
       EventHandler for PacketIn messages
        """
        msg = ev.msg

        # In OpenFlow, switches are called "datapaths".  Each switch gets its own datapath ID.
        # In the controller, we pass around datapath objects with metadata about each switch.
        dp = msg.datapath

        # Use this object to create packets for the given datapath
        ofctl = OfCtl.factory(dp, self.logger)

        in_port = msg.in_port
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            arp_msg = pkt.get_protocols(arp.arp)[0]

            if arp_msg.opcode == arp.ARP_REQUEST:

                self.logger.warning("Received ARP REQUEST on switch%d/%d:  Who has %s?  Tell %s",
                                    dp.id, in_port, arp_msg.dst_ip, arp_msg.src_mac)

                # TODO:  Generate a *REPLY* for this request based on your switch state

                # Here is an example way to send an ARP packet using the ofctl utilities
                r_mac = ""
                found = False
                for translation in self.tm.ip_to_mac:
                    if translation[0] == arp_msg.dst_ip:
                        r_mac = translation[1]
                        found = True
                        break
                if found:
                    ofctl.send_arp(vlan_id=VLANID_NONE, src_port=ofctl.dp.ofproto.OFPP_CONTROLLER, arp_opcode=2,
                                   dst_mac=arp_msg.src_mac, sender_mac=r_mac, sender_ip=arp_msg.dst_ip, target_ip=arp_msg.src_ip,
                                   target_mac=arp_msg.src_mac, output_port=in_port)

    def add_forwarding_rule(self, datapath, dl_dst, port):
        ofctl = OfCtl.factory(datapath, self.logger)
        actions = [datapath.ofproto_parser.OFPActionOutput(port)]
        ofctl.set_flow(cookie=0, priority=0, dl_type=ether_types.ETH_TYPE_IP, dl_vlan=VLANID_NONE, dl_dst=dl_dst,
                       actions=actions)
        print('forwarding_rule:\n    switch:%s\n    dl_dst: %s\n    port: %s' %
              (datapath.id, dl_dst, port))

    def delete_forwarding_rule(self, datapath, dl_dst):
        ofctl = OfCtl.factory(datapath, self.logger)
        match = datapath.ofproto_parser.OFPMatch(dl_dst=dl_dst)
        ofctl.delete_flow(cookie=0, priority=0, match=match)

    def flowtable_update(self):
        for device in self.tm.all_devices:
            if isinstance(device, TMHost):
                self.dijkstra(device)
        self.topology_show()
    
    def topology_show(self):
        print("------------Topology Table------------")
        print("Topology of Hosts:")
        for i in self.tm.all_devices:
            if isinstance(i, TMHost):
                self.logger.warning("    %s is connected to %s", i.name, i.neighbors[0][0].name)
        print("Topology of Switch:")
        for i in self.tm.all_devices:
            if isinstance(i, TMSwitch):
                self.logger.warning("    %s", i.name)
                for neighbor in i.neighbors:
                    if isinstance(neighbor[0], TMHost):
                        self.logger.warning("        Connected to %s by Port_%s", neighbor[0].name, neighbor[1].port_no)
                    if isinstance(neighbor[0], TMSwitch):
                        self.logger.warning("        Connected to %s by Port_%s", neighbor[0].name, neighbor[1].port_no)
        print("--------------------------------------")   

    def rules_update(self):
        for i in self.tm.all_devices:
            if isinstance(i, TMHost):
                for point, num_port in i.path:
                    point.actions = []
                    self.delete_forwarding_rule(point.get_dp(), "00:00:00:00:00:00")

        for i in self.tm.all_devices:
            if isinstance(i, TMHost):
                for point, num_port in i.path:
                    point.flag = False
                    self.delete_forwarding_rule(point.get_dp(), i.get_mac())
                    self.add_forwarding_rule(point.get_dp(), i.get_mac(), num_port)
                    datapath = point.get_dp()
                    point.actions += [datapath.ofproto_parser.OFPActionOutput(num_port)]
                    #self.add_forwarding_rule(point.get_dp(), "00:00:00:00:00:00", num_port)
        
        for i in self.tm.all_devices:
            if isinstance(i, TMHost):
                for point, num_port in i.path:
                    if not point.flag:
                        point.flag = True
                        ofctl = OfCtl.factory(point.get_dp(), self.logger)
                        ofctl.set_flow(cookie=0, priority=0, dl_type=ether_types.ETH_TYPE_IP, dl_vlan=VLANID_NONE, dl_dst="00:00:00:00:00:00", actions=point.actions)


    def dijkstra(self, start):
        q = queue.PriorityQueue(0)
        for device in self.tm.all_devices:
            if device is not start:
                device.distance = MAX
            else:
                device.distance = 0
            device.checked = False
            device.path = []
            device.shortestpath = []
            q.put((device.distance, device))

        while  q.qsize()>0:
            first = q.get()
            top = first[1]
            if isinstance(top, TMHost):
                if not top.checked:
                    top.checked = True
                    if top.distance == 0:
                        top.neighbors[0][0].distance = 1
                        #top.neighbors[0][0].shortestpath = top.shortestpath+[top.name]
                        q.put((1, top.neighbors[0][0]))
                    else:
                        continue
            elif isinstance(top, TMSwitch):
                for neighbor in top.neighbors:
                    neighbor_type_switch = isinstance(neighbor[0], TMSwitch)
                    if not neighbor[0].checked:
                        adjacent = False
                        for i in neighbor[0].neighbors:
                            if i[0] is top:
                                adjacent = True
                        if neighbor[1].is_live():
                            if (not neighbor_type_switch) or (neighbor_type_switch and adjacent):
                                if neighbor[0].distance < top.distance + 1:
                                    continue
                                neighbor[0].path = top.path + [(top, neighbor[1].port_no)]
                                neighbor[0].shortestpath = top.shortestpath + [top.name]
                                neighbor[0].distance = top.distance + 1
                                q.put((neighbor[0].distance, neighbor[0]))
                top.checked = True

        self.rules_update()
        
        # output the shortest path
        print("------------Shortest Path Table------------")
        print("From "+start.name)
        for device in self.tm.all_devices:
            if isinstance(device, TMHost):
                self.logger.warning("    To %s: shortest distance is %s,\n        path is:%s", device.name, device.distance, device.shortestpath)
        print("-------------------------------------------")

