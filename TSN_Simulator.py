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
############## DEFINE NODES CLASSES ##############
##################################################

# node base class
class Node:

    def __init__(self, id, name="unnamed"):
        self.node_type = str(self.__class__.__name__)  # this will be the same as the class name for each node
        self.id = id  # unique
        self.name = name
        self.ingress_traffic = []
        self.egress_traffic = []


    def to_string(self):
        return str(self.node_type+" (ID: "+str(self.id)+") "+str(self.name))



# end station type of node
class End_Station(Node):

    def __init__(self, id, name="unnamed"):
        super().__init__(id, name)
        self.type = e_es_types[0]  # default


    # function to send traffic from this node to a destination described in the traffic object it is sending
    def send(self, send_t):
        # TODO : error check make sure that send_t is a traffic object
        print("adding traffic", "\""+send_t+"\"", "to egress queue")
        self.egress_traffic.append(send_t)


    # somehow loop this or it activates when traffic has been sent to this node
    def on_receive(self):
        # maybe if ingress queue not empty do something here as a way of looping
        print("Received")
        pass


    ## setters
    def set_type(self, type):
        self.type = type



# switch type of node
class Switch(Node):

    def __init__(self, id, name="unnamed"):
        super().__init__(id, name)
        self.packets_transmitted = 0
        self.queue_delay = 0.0
        self.local_routing_table = -1  # to be set
        self.queue = -1  # to be set

        # TODO : queue_def is parsed outside of this object and is of type queue, each switch can be different


    # sends the traffic to destination from route in routing table
    def forward(self, destination):
        self.packets_transmitted += 1
        # TODO : implement destination lookup in local routing table and add to egress queue


    # call this a lot
    def recalculate_delay(self):
        # recalculate the delay based on current packet in and out time
        pass


    # setters
    def set_queue_def(self, queue_def):
        self.queue = queue_def


    def set_local_routing_table(self, routing_table_def):
        self.local_routing_table = routing_table_def



# controller type of switch
class Controller(Switch):

    def __init__(self, id, name="unnamed"):
        super().__init__(id, name)
        self.routing_table = -1  # the entire routing table is stored in this object as a dict
        # TODO : set queue type here


    def monitor_traffic(self):
        # every time anything passes through this switch we get stats from it here. Called every time
        pass


    def send_control(self, packet):
        # used to send control packets to other switches or end points specified in the packet
        pass


    def set_routing_table(self, main_routing_table):
        self.routing_table = main_routing_table  # the entire routing table is stored in this object




##################################################
############# DEFINE TRAFFIC CLASSES #############
##################################################

# base class traffic (abstraction of packets)
class Traffic():

    def __init__(self, source, destination):
        # get IDs
        self.source = source
        self.destination = destination  # list. May not need to be initialised



# define packets that belong to the traffic class (frame -> packet -> traffic)
# TODO : may need to have data in here somehow, or in frames
class Packet(Traffic):

    def __init__(self, source, destination, priority, name="unnamed", offset="0"):
        super().__init__(source, destination)
        self.arrival_time = 0.0  # TODO : set this to the NOW timestamp
        self.transmission_time = -1.0  # this is changed upon successful transmission from the node when it leaves the queue



# ST traffic type
class ST(Packet):
    # for this type of traffic we use the GCL so need to show this somehow

    def __init__(self, source, destination, priority, delay_jitter_constraints, period, deadline, \
                 name="unnamed", offset="0"):
        super().__init__(source, destination, 1, name, offset)  # priority 1
        self.delay_jitter_constraints = delay_jitter_constraints
        self.period = period
        self.hard_deadline = deadline



# non-st traffic type. Abstraction. No traffic should directly be NonST
# commonly called sporadic soft
class NonST(Packet):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 period, name="unnamed", offset="0"):
        super().__init__(source, destination, priority, name, offset)
        self.minimal_inter_release_time = minimal_inter_release_time
        self.delay_jitter_constraints = delay_jitter_constraints
        self.period = period



# sporadic hard type of nonST traffic
class Sporadic_Hard(NonST):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 period, deadline, name="unnamed", offset="0"):
        super().__init__(source, destination, 2, minimal_inter_release_time, delay_jitter_constraints, period, name, offset)  # priority 2
        self.hard_deadline = deadline



# sporadic soft type of nonST traffic
class Sporadic_Soft(NonST):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 period, deadline, name="unnamed", offset="0"):
        super().__init__(source, destination, 3, minimal_inter_release_time, delay_jitter_constraints, period, name, offset)  # priority 3
        self.soft_deadline = deadline



# best effort type of nonST traffic
class Best_Effort(NonST):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 period, name="unnamed", offset="0"):
        super().__init__(source, destination, 4, minimal_inter_release_time, delay_jitter_constraints, period, name, offset)  # priority 4




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
############# PARSE INPUTS FUNCTIONS #############
##################################################

## HELPERS
# helper function to recursively check switches are error free
def error_check_switch(switch):

    global g_node_id_dict  # for readability
    end_station_count = 0
    switch_count = 0
    child_nodes_count = len(switch)


    # check the switch itself for errors
    if(len(switch.keys()) != 2):  # switch must only have 2 attributes called "name" and "unique_id"
        print("ERROR: A switch has too many attributes")
        return -1
    if( ("unique_id" not in switch.keys()) or ("name" not in switch.keys()) ):
        print("ERROR: Invalid switch attribute names")
        return -1
    if(int(switch.get("unique_id")) in g_node_id_dict):  # make sure each ID is unique
        print("ERROR: Duplicate ID found (ID:", switch.get("unique_id")+")")
        return -1
    if(child_nodes_count < 1):  # must be at least 1 other node connected to a switch
        print("ERROR: There must be at least 1 end station connected to switch (ID:", switch.get("unique_id")+")")
        return -1


    # check children for errors
    for node in switch:
        if( (node.tag != "Switch") and (node.tag != "End_Station") ):  # only switches or end stations can be children of switches
            print("ERROR: Invalid switch node tag connected to switch (ID:", switch.get("unique_id")+")")
            return -1

        # child end station
        if(node.tag == "End_Station"):  # check any end stations for errors
            if(len(node.keys()) != 2):  # end stations must only have 2 attributes called "name" and "unique_id"
                print("ERROR: End Station has too many attributes")
                return -1
            if( ("unique_id" not in node.keys()) or ("name" not in node.keys()) ):
                print("ERROR: Invalid end station attribute names")
                return -1
            if(int(node.get("unique_id")) in g_node_id_dict):  # make srue we dont have any duplicate IDs
                print("ERROR: Duplicate ID found (ID:", node.get("unique_id")+")")
                return -1
            if(len(node) != 0):  # end stations are not allowed any children
                print("ERROR: End station (ID:", node.get("unique_id")+")", "has children")
                return -1
            if(int(node.get("unique_id")) in g_node_id_dict):  # make sure each ID is unique
                print("ERROR: Duplicate ID found (ID:", switch.get("unique_id")+")")
                return -1
            end_station_count += 1  # no errors, add to count
            end_station_node = End_Station(int(node.get("unique_id")), node.get("name"))  # create node
            g_node_id_dict[int(node.get("unique_id"))] = end_station_node  # switch and its children are error free, add its ID to list
        if(end_station_count < 1):  # must be at least 1 end station
            print("ERROR: There must be at least 1 end station connected to switch (ID:", switch.get("unique_id")+")")
            return -1

        # child switch
        if node.tag == "Switch":
            if error_check_switch(node) == -1:  # recursively check for errors on this switch and its children switches if any
                return -1
            if int(node.get("unique_id")) in g_node_id_dict:  # double check none of its children has its ID before adding it
                print("ERROR: Duplicate ID found (ID:", node.get("unique_id")+")")
                return -1
            switch_count += 1
            switch_node = Switch(int(node.get("unique_id")), node.get("name"))  # create node
            g_node_id_dict[int(node.get("unique_id"))] = switch_node  # switch and its children are error free, add its ID to list

    return 1



## PARSERS
# function to parse the network topology file and populate the network
def parse_network_topo(f_network_topo):

    global g_node_id_dict

    # parse XML file and get root
    parser = etree.XMLParser(ns_clean=True)
    tree = etree.parse(f_network_topo, parser)
    root = tree.getroot()


    ### Get info into easy to read variables and do some error checking
    ## Controller
    controller = root[0]
    if len(root) != 1:  # only 1 controller permitted
        print("ERROR: Invalid controller count")
        return -1
    if controller.tag != "Controller":  # controller must be called "Controller" at depth 1 in the XML
        print("ERROR: Controller missing or at incorrect depth")
        return -1
    if len(controller.keys()) != 2:  # controller must only have 2 attributes called "name" and "unique_id"
        print("ERROR: Controler has too many attributes")
        return -1
    if( ("unique_id" not in controller.keys()) or ("name" not in controller.keys()) ):
        print("ERROR: Invalid controller attribute names")
        return -1
    if controller.get("unique_id") != str(0):
        print("ERROR: Controller ID must be 0")
        return -1
    controller_node = Controller(0, controller.get("name"))  # create controller node with id 0 and name from file
    g_node_id_dict[0] = controller_node  # add controller to global node list


    ## Switches
    switch_count = len(root[0])
    if switch_count < 1:  # must be at least 1 switch
        print("ERROR: There must be at least 1 switch")
        return -1
    for switch in controller:
        if switch.tag != "Switch":  # make sure we only have switches and not end stations connected to the controller
            print("ERROR: Invalid switch node tag connected to the Controller")
            return -1
        if error_check_switch(switch) == -1:  # recursively check for errors on this switch and its children switches if any
            return -1
        if int(switch.get("unique_id")) in g_node_id_dict:  # double check none of its children has its ID before adding it
            print("ERROR: Duplicate ID found (ID:", switch.get("unique_id")+")")
            return -1
        switch_node = Switch(int(switch.get("unique_id")), switch.get("name"))  # create node
        g_node_id_dict[int(switch.get("unique_id"))] = switch_node  # switch and its children are error free, add its ID to list


    ### Finish up
    # check we havent exceeded the max count
    if len(g_node_id_dict) > MAX_NODE_COUNT:
        print("ERROR: Too many nodes:", len(g_node_id_dict), "(MAX:", str(MAX_NODE_COUNT)+")")
        return -1

    return 1



# function to parse the routing table from the network topo and populate the switches with routes (to be done after parsing network topo)
def parse_routing_table(f_network_topo):

    routing_table = {}

    # parse file and get root of XML
    parser = etree.XMLParser(ns_clean=True)
    tree = etree.parse(f_network_topo, parser)
    root = tree.getroot()


    # get a list of all switches and end stations from the network topo
    switch_list = []
    end_station_list = []
    for key in g_node_id_dict:
        if g_node_id_dict[key].node_type == "Switch":
            switch_list.append(key)
        if g_node_id_dict[key].node_type == "End_Station":
            end_station_list.append(key)
    switch_list.append(0)  # controller is also a switch

    # for every switch in the XML, add all its children to global routing table dictionary to be altered later
    for node in root.iter("Switch"):
        routing_table[int(node.get("unique_id"))] = [(int(es.get("unique_id")), int(node.get("unique_id"))) for es in node]
    routing_table[int(root[0].get("unique_id"))] = [(int(es.get("unique_id")), int(root[0].get("unique_id"))) for es in root[0]]  # controller is also a switch


    # go through dictionary and translate any switch IDs listed under children to the ES that switch links to
    # loop until no more switches in children
    while 1:
        changes = 0  # track amount of changes made so we can break out when we make no changes in a loop

        for switch_id in routing_table:  # for each switch in the routing table
            out_tuple = []  # prepare list to keep track of any hops for the entire switch we are checking
            switches_to_delete = []  # prepare list of elements that we are to delete upon completion of the scan

            for child_index in range(len(routing_table[switch_id])):  # check every child of the current switch
                if routing_table[switch_id][child_index][0] in switch_list:  # if the child of a switch is another switch we have found a hop point
                    changes += 1  # increase change count

                    # insert hop entries from child switch
                    for node in routing_table[routing_table[switch_id][child_index][0]]:  # for each node connected to the child hop switch

                        # build the translation in the form (end_station_id, hop_switch_id)
                        part_out_tuple = []
                        part_out_tuple.append(node[0])  # get end_station_id from child switch

                        if routing_table[switch_id][child_index][1] == switch_id:
                            part_out_tuple.append(routing_table[switch_id][child_index][0])  # insert direct hop switch_id
                        else:
                            part_out_tuple.append(routing_table[switch_id][child_index][1])  # insert indirect hop switch_id

                        # append translation to the new lists so we do not modify the live list
                        out_tuple.append(tuple(part_out_tuple))
                    switches_to_delete.append(routing_table[switch_id][child_index])  # remember the broken entry to delete later


            # finally modify the live switch dict to reflect new changes
            for element in switches_to_delete:
                routing_table[switch_id].remove(element)  # delete broken entries
            for hop in out_tuple:
                routing_table[switch_id].append(hop)  # insert new hop entries into the list


        # we can leave the while loop if we make no changes
        if changes == 0:
            break


    # next make sure every end station is included in the routing table. If any are missing it means they are NOT children, so add the parent as an entry
    for switch_id in routing_table:
        missing_end_stations = end_station_list.copy()  # create list of all end stations

        for child_id in routing_table[switch_id]:  # check each child of the switch
            if child_id[0] in missing_end_stations:
                missing_end_stations.remove(child_id[0])  # remove stations that are present form the list so we have a list of missing end station ids

        # add entries for each end station that is missing
        for node in root.iter("Switch"):
            if int(node.get("unique_id")) == switch_id:  # find switch in XML so we can get the parent
                for end_station in missing_end_stations:
                    routing_table[switch_id].append(tuple( (end_station, int(node.getparent().get("unique_id"))) ))  # append tuple of (es_id, sw_parent) to routing


    # error checking
    # each switch should have the same amount of children representing every end station
    for key in routing_table:
        if len(routing_table[key]) != len(end_station_list):
            print("ERROR: Entry \""+key+"\"", "in the global routing table has an incorrect amount of children")
            return -1

    # each switch should be present in the routing table
    if len(routing_table) != len(switch_list):
        print("ERROR: Incorrect amount of switches present in the global routing table")
        return -1


    # populate switch objects with their appropriate routing table
    for key in g_node_id_dict:
        if key in routing_table:
            if key == 0:  # add entire routing table to the controller
                g_node_id_dict[key].set_routing_table(routing_table)
                g_node_id_dict[key].set_local_routing_table(routing_table[key])

            else:  # only add local routing table to switches
                g_node_id_dict[key].set_local_routing_table(routing_table[key])

    return 1




##################################################
######## GET INPUT FILES OR GENERATE THEM ########
##################################################
# TODO : Have option to input file name if none provided here,
#        or to generate a new file via a crude generator script

# specify file paths and names
network_topo_file  = "example_network_topology.xml"



### Parse given files
# network topo
f = Path(network_topo_file)
if f.is_file():
    if(parse_network_topo(network_topo_file) == -1):
        print("ERROR: In file:", "\""+network_topo_file+"\"")
        exit()
    else:
        print("Successfully parsed network topology file:", "\""+network_topo_file+"\"")
else:
    print("ERROR: Network topology not found:", "\""+network_topo_file+"\"")
    exit()


# parse routing table from the network topology file
if f.is_file():
    if(parse_routing_table(network_topo_file) == -1):
        print("ERROR: In file:", "\""+network_topo_file+"\"")
        exit()
    else:
        print("Successfully parsed routing table from file:", "\""+network_topo_file+"\"")
else:
    print("ERROR: Network topology file not found:", "\""+network_topo_file+"\"")
    exit()




##################################################
################### DEBUG CODE ###################
##################################################

print()
print("TEST START")
print()

print(g_node_id_dict[0].toString())
g_node_id_dict[0].set_queue_def(2)
print("TYPE:", g_node_id_dict[0].node_type)
print("rtable for Controller id 0:", g_node_id_dict[0].local_routing_table)
print("qdef:", g_node_id_dict[0].queue)




print()
print("TEST END")




















# whitespace
