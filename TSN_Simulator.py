"""
Main TSN Simulator

Specify file locations for neccesay files (Network Topo, Routing Table, Traffic Definition, GCL, Queue definition)

"""

##################################################
##################### IMPORT #####################
##################################################

from pathlib import Path
from lxml import etree



## global variables
MAX_NODE_COUNT = 100
MAX_TRAFFIC_COUNT = 1000

e_es_types = ["sensor", "control"]  # possible end station types
e_queue_types = ["FIFO"]  # possible queue types

g_node_id_dict = {}



##################################################
######## GET INPUT FILES OR GENERATE THEM ########
##################################################

# specify file paths and names
f_network_topo = "example_network_topology.xml"


# check if files exist
## TODO : this can be in a for loop for each file type

f = Path(f_network_topo)
if f.is_file():
    print("FOUND:", f_network_topo)




##################################################
############## DEFINE NODES CLASSES ##############
##################################################

# node base class
class Node:

    def __init__(self, id, name="unnamed"):
        self.id = id
        self.name = name
        self.ingress_traffic = []
        self.egress_traffic = []



# end station type of node
class End_Station(Node):

    def __init__(self, id, name="unnamed"):
        Node.__init__(self, id, name)
        self.type = e_es_types[0]  # default


    # function to send traffic from this node to a destination described in the traffic object it is sending
    def send(self, send_t):
        # TODO : error check make sure that send_t is a traffic object
        print("adding traffic", "\""+send_t+"\"", "to egress queue")
        self.egress_traffic.append(send_t)


    # somehow loop this or it activates when traffic has been sent to this node
    def on_receive(self):
        # maybe if ingress queue not empty do something here
        print("Received")
        pass


    ## setters
    def set_type(self, type):
        self.type = type



# switch type of node
class Switch(Node):

    def __init__(self, id, name="unnamed"):
        Node.__init__(self, id, name)
        self.packets_transmitted = 0
        self.queue_delay = 0.0
        self.local_routing_table = -1  # to be set
        self.queue = -1  # to be set

        # TODO : queue_def is parsed outside of this object and is of type queue, each switch should be different
        # TODO : routing table should be passed in and then parsed in the object to get local routing table


    # sends the traffic to destination from route in routing table
    def forward(self, destination):
        self.packets_transmitted += 1


    # call this a lot
    def recalculate_delay(self):
        pass
        # recalculate the delay based on current packet in and out time


    # setters
    def set_queue_def(self, queue_def):
        self.queue = queue_def

    def set_routing_table(self, routing_table_def):
        self.routing_table = routing_table_def



# controller type of switch
class Controller(Switch):

    def __init__(self, id, name="unnamed"):
        Switch.__init__(self, id, name)
        self.routing_table = -1  # to be set


    def monitor_traffic(self):
        # every time anything passes through this switch we get stats from it here. Called every time
        pass


    def send_control(self, packet):
        # used to send control packets to other switches or end points specified in the packet
        pass


    # setters
    def set_queue_def(self, queue_def):
        Switch.set_queue_def(self, queue_def)

    def set_routing_table(self, f_routing_table):
        self.routing_table = f_routing_table

    def set_local_routing_table(self, routing_table_def):  # may not need this. May not need both a local routing and full routing
        Switch.set_routing_table(self, routing_table_def)




##################################################
############# DEFINE TRAFFIC CLASSES #############
##################################################

# base class traffic (abstraction of packets)
def Traffic():

    def __init__(self, source, destination):
        # get IDs
        self.source = source
        self.destination = destination  # list




# define packets that belong to the traffic class (frame -> packet -> traffic)
# TODO : may need to have data in here somehow, or in frames
def Packet(Traffic):

    def __init__(self, source, destination, priority, name="unnamed", offset="0"):
        self.arrival_time = 0.0  # TODO : set this to the NOW timestamp
        self.transmission_time = -1.0  # this is changed upon successful transmission from the node when it leaves the queue

        Traffic.__init__(self, source, destination)



# ST traffic type
def ST(Packet):

    def __init__(self, source, destination, priority, delay_jitter_constraints, period, deadline, \
                 name="unnamed", offset="0"):

        self.delay_jitter_constraints = delay_jitter_constraints
        self.period = period
        self.hard_deadline = deadline

        Packet.__init__(self, source, destination, 1, name, offset)
        # for this type of traffic we use the GCL so need to show this somehow



# non-st traffic type
def NonST(Packet):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 period, name="unnamed", offset="0"):

        self.minimal_inter_release_time = minimal_inter_release_time
        self.delay_jitter_constraints = delay_jitter_constraints
        self.period = period

        Packet.__init__(self, source, destination, priority, name, offset)



# sporadic hard type of nonST traffic
def Sporadic_Hard(NonST):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 period, deadline, name="unnamed", offset="0"):

        self.hard_deadline = deadline

        NonST.__init__(self, source, destination, 2, minimal_inter_release_time, delay_jitter_constraints, \
                       period, name, offset)



# sporadic soft type of nonST traffic
def Sporadic_Soft(NonST):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 period, deadline, name="unnamed", offset="0"):

        self.soft_deadline = deadline

        NonST.__init__(self, source, destination, 3, minimal_inter_release_time, delay_jitter_constraints, \
                       period, name, offset)



# best effort type of nonST traffic
def Best_Effort(NonST):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 period, name="unnamed", offset="0"):

        NonST.__init__(self, source, destination, 4, minimal_inter_release_time, delay_jitter_constraints, \
                       period, name, offset)




##################################################
############## DEFINE OTHER CLASSES ##############
##################################################

# queue class (should be present in each switch)
class Queue:
    def __init__(self, ST_count, emergency_count, sporadic_count, nonST_count, BE_count, offline_GCL, \
                 ST_type=e_queue_types[0], emergency_type=e_queue_types[0], sporadic_type=e_queue_types[0], \
                 nonST_type=e_queue_types[0], BE_type=e_queue_types[0]):

        # setup queues and their type
        self.ST_count = ST_count
        self.ST_type = ST_type
        self.emergency_count = emergency_count
        self.emergency_type = emergency_type
        self.sporadic_count = sporadic_count
        self.sporadic_type = sporadic_type
        self.nonST_count = nonST_count
        self.nonST_type = nonST_type
        self.BE_count = BE_count
        self.BE_type = BE_type

        # setup GCL details
        self.active_GCL = offline_GCL
        self.offline_GCL = offline_GCL


    # changes the active GCL in some way
    def modify_GCL(self):
        pass


    # makes sure that the frame is set up correctly and passes the acceptance test
    def acceptance_test(self, frame):
        return True

    def packet_ingress(self, packet):
        pass

    def packet_egress(self, packet):
        pass




##################################################
################## PARSE INPUTS ##################
##################################################

# helper function to recursively check switches are error free
def error_check_switch(switch):

    global g_node_id_dict
    end_station_count = 0
    child_nodes_count = len(switch)

    # check the switch itself for errors
    if(len(switch.keys()) != 2):  # switch must only have 2 attributes called "name" and "unique_id"
        print("ERROR: A switch has too many attributes in file:", "\""+f_network_topo+"\"")
        return -1
    if( ("unique_id" not in switch.keys()) or ("name" not in switch.keys()) ):
        print("ERROR: Invalid switch attribute names in file:", "\""+f_network_topo+"\"")
        return -1
    if(int(switch.get("unique_id")) in g_node_id_dict):  # make sure each ID is unique
        print("ERROR: Duplicate ID found (ID:", switch.get("unique_id")+")", "in file:", "\""+f_network_topo+"\"")
        return -1
    if(child_nodes_count < 1):  # must be at least 1 other node connected to a switch
        print("ERROR: There must be at least 1 end station connected to switch (ID:", switch.get("unique_id")+")", "in file:", "\""+f_network_topo+"\"")
        return -1


    # check children for errors
    for node in switch:
        if( (node.tag != "Switch") and (node.tag != "End_Station") ):  # only switches or end stations can be children of switches
            print("ERROR: Invalid switch node tag connected to switch (ID:", switch.get("unique_id")+")", "in file:", "\""+f_network_topo+"\"")
            return -1

        if(node.tag == "End_Station"):  # check any end stations for errors
            if(len(node.keys()) != 2):  # end stations must only have 2 attributes called "name" and "unique_id"
                print("ERROR: End Station has too many attributes in file:", "\""+f_network_topo+"\"")
                return -1
            if( ("unique_id" not in node.keys()) or ("name" not in node.keys()) ):
                print("ERROR: Invalid end station attribute names in file:", "\""+f_network_topo+"\"")
                return -1
            if(int(node.get("unique_id")) in g_node_id_dict):  # make srue we dont have any duplicate IDs
                print("ERROR: Duplicate ID found (ID:", node.get("unique_id")+")", "in file:", "\""+f_network_topo+"\"")
                return -1
            if(len(node) != 0):  # end stations are not allowed any children
                print("ERROR: End station (ID:", node.get("unique_id")+")", "has children in file:", "\""+f_network_topo+"\"")
                return -1
            if(int(node.get("unique_id")) in g_node_id_dict):  # make sure each ID is unique
                print("ERROR: Duplicate ID found (ID:", switch.get("unique_id")+")", "in file:", "\""+f_network_topo+"\"")
                return -1
            end_station_count += 1  # no errors, add to count
            end_station_node = End_Station(int(node.get("unique_id")), node.get("name"))  # create node
            g_node_id_dict[int(node.get("unique_id"))] = end_station_node  # switch and its children are error free, add its ID to list

        if(end_station_count < 1):  # must be at least 1 end station
            print("ERROR: There must be at least 1 end station connected to switch (ID:", switch.get("unique_id")+")", "in file:", "\""+f_network_topo+"\"")
            return -1

        if(node.tag == "Switch"):  # need to recursively check further switches
            inner_switch_check = error_check_switch(node)  # recursively check for errors on this switch and its children switches if any
            if(inner_switch_check == -1):
                return -1
            switch_node = Switch(int(node.get("unique_id")), node.get("name"))  # create node
            g_node_id_dict[int(node.get("unique_id"))] = switch_node  # switch and its children are error free, add its ID to list

    return 1



# function to parse the network topology file and populate the network
def parse_network_topo(f_network_topo):

    global g_node_id_dict

    parser = etree.XMLParser(ns_clean=True)
    tree = etree.parse(f_network_topo, parser)
    root = tree.getroot()

    print(etree.tostring(root, pretty_print=True).decode())
    print()

    ### Get info into easy to read variables and do some error checking
    ## Controller
    controller = root[0]
    if(len(root) != 1):  # only 1 controller permitted
        print("ERROR: Invalid controller count in file:", "\""+f_network_topo+"\"")
        return -1
    if(controller.tag != "Controller"):  # controller must be called "Controller" at depth 1 in the XML
        print("ERROR: Controller missing or at incorrect depth in file:", "\""+f_network_topo+"\"")
        return -1
    if(len(controller.keys()) != 2):  # controller must only have 2 attributes called "name" and "unique_id"
        print("ERROR: Controler has too many attributes in file:", "\""+f_network_topo+"\"")
        return -1
    if( ("unique_id" not in controller.keys()) or ("name" not in controller.keys()) ):
        print("ERROR: Invalid controller attribute names in file:", "\""+f_network_topo+"\"")
        return -1
    if(controller.get("unique_id") != str(0)):
        print("ERROR: Controller ID must be 0 in file:", "\""+f_network_topo+"\"")
        return -1
    controller_node = Controller(0, controller.get("name"))  # create controller node with id 0 and name from file
    g_node_id_dict[0] = controller_node  # add controller to global node list


    ## Switches
    switch_count = len(root[0])
    if(switch_count < 1):  # must be at least 1 switch
        print("ERROR: There must be at least 1 switch in file:", "\""+f_network_topo+"\"")
        return -1

    for switch in controller:
        if(switch.tag != "Switch"):  # make sure we only have switches and not end stations connected to the controller
            print("ERROR: Invalid switch node tag connected to the Controller in file:", "\""+f_network_topo+"\"")
            return -1

        if(error_check_switch(switch) == -1):  # recursively check for errors on this switch and its children switches if any
            return -1
        switch_node = Switch(int(switch.get("unique_id")), switch.get("name"))  # create node
        g_node_id_dict[int(switch.get("unique_id"))] = switch_node  # switch and its children are error free, add its ID to list


    ### Finish up
    if(len(g_node_id_dict) > MAX_NODE_COUNT):
        print("ERROR: Too many nodes (MAX:", MAX_NODE_COUNT+")", "in file:", "\""+f_network_topo+"\"")
        return -1














## CODE

p1 = End_Station(1, e_es_types[0])
print(p1.type)
p1.send("")
print()
parse_network_topo(f_network_topo)
print()

print("TEST END")




















# whitespace
