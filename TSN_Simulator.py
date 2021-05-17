"""
Main TSN Simulator

Specify file locations for neccesay files (Network Topo, Traffic Definition, GCL, Queue definition)
"""

##################################################
############## IMPORT AND VARIABLES ##############
##################################################

# libraries
import random
from pathlib import Path
from lxml import etree

# scripts
import generator_utilities as gen_utils
import crude_topo_generator as network_topo_gen  # network topology generator
import crude_queue_def_generator as queue_def_gen  # queue definition generator
import crude_traffic_def_generator as traffic_def_gen  # traffic definition generator
# GCL should be made manually ahdering to standards in the UML diagrams -> T(digit){-T(digit)} (8-bits)

# global variables
g_timestamp = 0
g_generic_traffics_dict = {}  # dictionary of generic traffic rules from file - key is ID
g_node_id_dict = {}  # key is node id, value is node object
g_offline_GCL = {}  # key is timestamp, value is the gate state at that timestamp
g_current_GCL_state = ""  # state of GCL shared across entire simulator, to be changed according to GCL and timestamp
# should only change gate state if we have a key for that timestamp, else leave it as previous value
g_packet_latencies = []  # list to store a list of every packet latency
g_queueing_delays = []




##################################################
################# USER  SETTINGS #################
##################################################

# global variables to set
MAX_NODE_COUNT = 100
MAX_TRAFFIC_COUNT = 1000
SIM_DEBUG = 1  # debug for simulator to see timestamps

# global enums
e_es_types = ["sensor", "control"]  # possible end station types
e_queue_schedules = ["FIFO"]  # possible queue schedules
e_queue_type_names = ["ST", "Emergency", "Sporadic_Hard", "Sporadic_Soft", "BE"]  # possible queue types

# specify file paths and names
# TODO : Have option to input file name if none provided here
using = "example"
using = "M"
files_directory       = "simulator_files\\"
network_topo_file       = files_directory+using+"_network_topology.xml"
queue_definition_file   = files_directory+using+"_queue_definition.xml"
GCL_file                = files_directory+using+"_gcl.txt"
traffic_definition_file = files_directory+using+"_traffic_definition.xml"




##################################################
############## DEFINE NODES CLASSES ##############
##################################################

# node base class
class Node():

    def __init__(self, id, name="unnamed"):
        self.node_type = str(self.__class__.__name__)  # this will be the same as the class name for each node
        self.id = id  # unique
        self.name = name
        self.ingress_traffic = []
        self.egress_traffic = []


    def RX_packet(self, packet):
        self.ingress_traffic.append(packet)


    def to_string(self):
        # node type
        output_str = str(self.node_type) + ":"

        # formatting
        if self.node_type == "Controller":
            output_str += " "
        if self.node_type == "Switch":
            output_str += "     "

        # attributes
        output_str += " (ID: "+str(self.id)+") (Name: "+str(self.name)+") "

        # display traffic gen paramerters
        if self.node_type == "End_Station":
            output_str += str(self.packet.to_string())

        return output_str



# end station type of node
class End_Station(Node):

    def __init__(self, id, parent_id, name="unnamed"):
        super().__init__(id, name)
        self.type = e_es_types[0]  # default
        self.parent_id = int(parent_id)


    # check if it is packet generation time and if so put new packet in egress
    def check_to_generate(self):
        # TODO : Add checks for other types of traffic (SH, SS, BE) and appropriate random generator functions

        # determine type as ST generates differently
        if self.t_type == "ST":
            if g_timestamp % self.t_period == 0:  # if we are at its period

                # generate new packet and add to egress
                packet = ST(self.id, self.t_dest, self.t_delay_jitter, self.t_period, self.t_deadline,
                            self.t_name, self.t_offset)
                self.egress(packet)
                if SIM_DEBUG:  # for debug
                    print("[T", str(g_timestamp).zfill(3)+"]", "Adding newly generated", str(self.t_type), "packet", \
                          "\""+str(packet.name)+"\"", "to egress queue of ES", "\""+str(self.id)+"\"")

        return 1


    # function to recieve packets in ingress queue
    def digest_packets(self):
        if len(self.ingress_traffic) == 0:  # do nothing if queue empty
            return 0

        # loop over all packets in ingress queue
        for packet in self.ingress_traffic:
            packet.set_arrival_time(g_timestamp)

            if SIM_DEBUG:  # for debug
                print("[T", str(g_timestamp).zfill(3)+"]", "Recieved", str(packet.__class__.__name__), "packet", \
                      "\""+str(packet.name)+"\"", "from source ES", "\""+str(packet.source)+"\"", \
                      "at final destination ES", "\""+str(self.id)+"\"", "with latency", \
                      "\""+str(int(packet.arrival_time)-int(packet.transmission_time))+"\"")
            g_packet_latencies.append(int(packet.arrival_time)-int(packet.transmission_time))  # add latency to list
        self.ingress_traffic = []  # clear queue as we have ingested everything

        return 1


    # function to send all traffic from this nodes egress queue to parent switch
    def flush_egress(self):
        # should only be able to generate 1 packet at a time, but allow burst sending if we inform the user
        if len(self.egress_traffic) > 1:
            print("WARNING: Egress queue of ES:", str(self.id), "has length:", str(len(self.egress_traffic))+".", \
                  "Burst sending all packets to parent Switch:", str(self.parent_id))

        # burst send all packets to parent switch's ingress queue to be digested
        for packet in self.egress_traffic:
            if SIM_DEBUG:  # for debug
                print("[T", str(g_timestamp).zfill(3)+"]", "Sending", str(packet.__class__.__name__), "Traffic", \
                      "\""+str(packet.name)+"\"", "to parent Switch", "\""+str(self.parent_id)+"\"", \
                      "from egress queue of ES", "\""+str(self.id)+"\"")

            g_node_id_dict[self.parent_id].RX_packet(packet)
        self.egress_traffic = []  # empty queue as we have sent all packets
        return 1


    # function to add a packet to the egress queue with error checking
    def egress(self, packet):
        # error check to make sure it is an actual traffic object
        if packet.__class__.__bases__[0].__bases__[0].__name__ == "Traffic":  # PARENT of PARENT of packet
            self.egress_traffic.append(packet)
            return 1
        else:
            return 0


    ## Setters
    def set_traffic_rules(self, rules):
        # TODO : add other traffic types

        if 0:  # for debugging
            print("Rule properties:")
            print("Source:", self.id)
            for entry in rules:
                print(entry+":", rules[entry])
            print()

        # erorr check destination
        if str(rules["destination_id"]) == str(self.id):  # error check cant have destination be itself
            print("CRITICAL ERROR: Cannot have Traffic rule destination_id be the same ID as the source in ES", \
                  "\""+str(self.id)+"\"")
            return 0

        # extract shared attributess
        self.t_name = rules["name"]
        self.t_offset = rules["offset"]
        self.t_type = rules["type"]
        self.t_dest = rules["destination_id"]

        # if destination_id is 0, we need to change it to a random ES ID
        if int(self.t_dest) == 0:
            # get list of end stations
            es_list = []
            for node in g_node_id_dict:
                if g_node_id_dict[node].node_type == "End_Station":
                    es_list.append(node)
            es_list.remove(self.id)  # remove this end station
            self.t_dest = str(random.choice(es_list))  # pick a random node from the list


        # extract ST attributes
        if self.t_type == "ST":
            self.t_period = rules["period"]
            self.t_deadline = rules["hard_deadline"]
            self.t_delay_jitter = rules["max_release_jitter"]

        return 1


    def set_type(self, type):
        self.type = type
        return 1



# switch type of node
class Switch(Node):

    def __init__(self, id, name="unnamed"):
        super().__init__(id, name)
        self.available_packets = []
        self.packets_transmitted = 0
        self.total_queue_delay = 0
        self.average_queue_delay = 0.0
        self.local_routing_table = -1  # to be set

        # queues
        self.queue_definition = -1  # to be set
        self.ST_queue = []
        self.EM_queue = []
        self.SH_queue = []
        self.SS_queue = []
        self.BE_queue = []


    # filters packets in the ingress queue into the relevant Traffic queue within the switch according to the queue_def
    def ingress_packets(self):
        # TODO : acceptance function somehow
        # TODO : work out how to put traffics in different queues of same type

        # if ingress queue is empty do nothing
        if len(self.ingress_traffic) == 0:
            return 0

        # shuffle ingress to avoid ES bias if there is more than 1 packet
        if len(self.ingress_traffic) > 1:
            random.shuffle(self.ingress_traffic)

        # each packet gets added to the relevant queue within the switch
        final_ingress = self.ingress_traffic.copy()  # use a copy of this so we do not alter the live list when removing packets
        for packet in self.ingress_traffic:
            if SIM_DEBUG:  # debug
                print("[T", str(g_timestamp).zfill(3)+"]", "Found", packet.__class__.__name__, "Traffic", "\""+str(packet.name)+"\"", \
                      "from ES", "\""+str(packet.source)+"\"", "in ingress queue of Switch", "\""+str(self.id)+"\"")

            # add queue enter timestamp
            packet.set_queue_enter(g_timestamp)

            # ST
            if packet.__class__.__name__ == "ST":
                # TODO : figure out how ingress selects which queue (if > 1) to put traffic in
                self.ST_queue[0].append(packet)
                final_ingress.remove(packet)

            # SH
            if packet.__class__.__name__ == "Sporadic_Hard":
                # TODO : figure out how ingress selects which queue (if > 1) to put traffic in
                self.SH_queue[0].append(packet)
                final_ingress.remove(packet)

            # SS
            if packet.__class__.__name__ == "Sporadic_Soft":
                # TODO : figure out how ingress selects which queue (if > 1) to put traffic in
                self.SS_queue[0].append(packet)
                final_ingress.remove(packet)

            # BE
            if packet.__class__.__name__ == "BE":
                # TODO : figure out how ingress selects which queue (if > 1) to put traffic in
                self.BE_queue[0].append(packet)
                final_ingress.remove(packet)


        self.ingress_traffic = final_ingress
        return 1


    # applies scheduling to the 8 queues to get packets in the egress section
    def cycle_queues(self):
        # TODO : implement other traffic types and other schedules go in here
        gcl_pos = 0
        self.available_packets = []

        # ST queues
        for i in range(len(self.ST_queue)):
            # first check the GCL to see if the queue is open
            gcl_pos += 1  # for next iteration
            if g_current_GCL_state[gcl_pos-1] == str(0):  # if gate is shut
                continue  # skip this iteration

            # if open, copy packet to temp queue depending on its schedule to show it is available to be sent
            if self.queue_definition.ST_schedule == e_queue_schedules[0]:  # FIFO
                if len(self.ST_queue[i]) != 0:  # if queue isnt empty
                    if SIM_DEBUG:  # for debug
                        print("[T", str(g_timestamp).zfill(3)+"]", "[FIFO] Adding ST packet", "\""+str(self.ST_queue[i][0].name)+"\"", \
                              "from ES", "\""+str(self.ST_queue[i][0].source)+"\"", "to \"available_packets\" queue of Switch", \
                              "\""+str(self.id)+"\"")

                    # add queue number, and packet to available packet
                    self.available_packets.append((i, self.ST_queue[i][0]))  # FIFO part here.

            # TODO : EDF would loop entire queue to find shortest deadline and then add etc e.g:
            # if self.queue_definition.ST_schedule == e_queue_schedules[1]:  # EDF
            # for packet in queue:
            #   find earliest deadline, add to available packets

        return 1


    # function to check available packets list, apply strict priority ordering, and send 1 packet
    def egress_packets(self):
        # now we send highest priority packet from the list of available packets
        if len(self.available_packets) == 0:  # if available packets queue empty, do nothing
            return 0

        # find highest priority packet out of all packets available to be sent
        packet_to_send = self.available_packets[0]
        for packet in self.available_packets:
            if packet[1].priority < packet_to_send[1].priority:
                packet_to_send = packet

        # send it
        self.forward(packet_to_send[1])

        # remove it from its original queue
        queue_type = packet_to_send[1].__class__.__name__
        queue_number = packet_to_send[0]
        if queue_type == "ST":
            self.ST_queue[queue_number].remove(packet_to_send[1])
        elif queue_type == "Sporadic_Hard":
            self.SH_queue[queue_number].remove(packet_to_send[1])
        elif queue_type == "Sporadic_Soft":
            self.SS_queue[queue_number].remove(packet_to_send[1])
        elif queue_type == "Best_Effort":
            self.BE_queue[queue_number].remove(packet_to_send[1])

        return 1


    # sends the traffic to destination from route in routing table
    # TODO : This may need to be translated into sending multiple frames looped so it can be preempted
    def forward(self, packet):
        self.packets_transmitted += 1
        self.recalculate_packet_delay(packet)

        # get hop from routing table
        hop = -1
        for route in self.local_routing_table:
            if int(route[0]) == int(packet.destination):
                hop = route[1]
                break  # found

        if SIM_DEBUG:  # debug
            print("[T", str(g_timestamp).zfill(3)+"]", "Sending", str(packet.__class__.__name__), \
                  "packet", "\""+str(packet.name)+"\"", "from ES", "\""+str(packet.source)+"\"", \
                  "in egress queue of Switch", "\""+str(self.id)+"\"", \
                  "to node ID", "\""+str(packet.destination)+"\"" if int(hop) == int(self.id) else "\""+str(hop)+"\"")

        # if hop is this switch we can send packet directly to the ES else we send to next switch
        g_node_id_dict[int(packet.destination) if int(hop) == int(self.id) else int(hop)].RX_packet(packet)

        return 1


    # function that recalculates queueing delay for this switch
    def recalculate_packet_delay(self, packet):
        packet.set_queue_leave(g_timestamp)  # set the queue_leave time for this packet
        queue_delay = int(int(packet.queue_leave)-int(packet.queue_enter))  # get the time it has been in the queue
        g_queueing_delays.append(queue_delay)  # add to global array

        # change local variables
        self.total_queue_delay += queue_delay  # cumulative
        self.average_queue_delay = int(self.total_queue_delay) / int(self.packets_transmitted)

        return 1


    ## Setters
    def set_queue_def(self, queue_def):
        self.queue_definition = queue_def

        # put empty lists in each queue type to signify how many queues each queue type has
        [self.ST_queue.append([]) for i in range(self.queue_definition.ST_count)]
        [self.EM_queue.append([]) for i in range(self.queue_definition.emergency_count)]
        [self.SH_queue.append([]) for i in range(self.queue_definition.sporadic_hard_count)]
        [self.SS_queue.append([]) for i in range(self.queue_definition.sporadic_soft_count)]
        [self.BE_queue.append([]) for i in range(self.queue_definition.BE_count)]

        return 1


    def set_local_routing_table(self, routing_table_def):
        self.local_routing_table = routing_table_def
        return 1



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


    ## Setters
    def set_routing_table(self, main_routing_table):
        self.routing_table = main_routing_table  # the entire routing table is stored in this object
        return 1




##################################################
############# DEFINE TRAFFIC CLASSES #############
##################################################

# base class traffic (abstraction of packets)
class Traffic():

    def __init__(self, source, destination):
        # get IDs
        self.source = source
        self.destination = destination  # list. May not need to be initialised


    # setters
    def set_dest(self, dest):
        self.destination = dest



# define packets that belong to the traffic class (frame -> packet -> traffic)
# TODO : may need to have data in here somehow, or in frames
class Packet(Traffic):

    def __init__(self, source, destination, priority, name="unnamed", offset="0"):
        super().__init__(source, destination)
        self.arrival_time = -1
        self.transmission_time = g_timestamp
        self.queue_enter = -1
        self.queue_leave = -1
        self.priority = priority
        self.name = name
        self.offset = offset


    ## Setters
    def set_arrival_time(self, timestamp):
        self.arrival_time = timestamp
        return 1


    def set_queue_enter(self, timestamp):
        self.queue_enter = timestamp
        return 1


    def set_queue_leave(self, timestamp):
        self.queue_leave = timestamp
        return 1



# ST traffic type
class ST(Packet):
    # for this type of traffic we use the GCL so need to show this somehow

    def __init__(self, source, destination, delay_jitter_constraints, period, deadline, \
                 name="unnamed", offset="0"):
        super().__init__(source, destination, 1, name, offset)  # priority 1
        self.delay_jitter_constraints = int(delay_jitter_constraints)
        self.period = int(period)
        self.hard_deadline = int(deadline)


    def to_string(self):
        output_str = "Packet Definition: "
        output_str += "(Type: " + str(self.__class__.__name__)
        output_str += ") (Source: " + str(self.source)
        output_str += ") (Priority: " + str(self.priority)
        output_str += ") (Deadline: " + str(self.hard_deadline)
        output_str += ") (Period: " + str(self.period)
        output_str += ") (Jitter: " + str(self.delay_jitter_constraints)
        output_str += ")"

        return output_str



# non-st traffic type. Abstraction. No traffic should directly be NonST
class NonST(Packet):

    def __init__(self, source, destination, priority, minimal_inter_release_time, delay_jitter_constraints, \
                 name="unnamed", offset="0"):
        super().__init__(source, destination, priority, name, offset)
        self.minimal_inter_release_time = minimal_inter_release_time
        self.delay_jitter_constraints = delay_jitter_constraints



# sporadic hard type of nonST traffic
class Sporadic_Hard(NonST):

    def __init__(self, source, destination, minimal_inter_release_time, delay_jitter_constraints, \
                 deadline, name="unnamed", offset="0"):
        super().__init__(source, destination, 2, minimal_inter_release_time, delay_jitter_constraints, name, offset)  # priority 2
        self.hard_deadline = deadline



# sporadic soft type of nonST traffic
class Sporadic_Soft(NonST):

    def __init__(self, source, destination, minimal_inter_release_time, delay_jitter_constraints, \
                 deadline, name="unnamed", offset="0"):
        super().__init__(source, destination, 3, minimal_inter_release_time, delay_jitter_constraints, name, offset)  # priority 3
        self.soft_deadline = deadline



# best effort type of nonST traffic
class Best_Effort(NonST):

    def __init__(self, source, destination, minimal_inter_release_time, delay_jitter_constraints, \
                 name="unnamed", offset="0"):
        super().__init__(source, destination, 4, minimal_inter_release_time, delay_jitter_constraints, name, offset)  # priority 4




##################################################
############## DEFINE OTHER CLASSES ##############
##################################################

# queue class (should be present in each switch)
class Queue():

    def __init__(self, ST_count, emergency_count, sporadic_hard_count, sporadic_soft_count, BE_count, \
                 ST_schedule=e_queue_schedules[0], emergency_schedule=e_queue_schedules[0], \
                 sporadic_hard_schedule=e_queue_schedules[0], sporadic_soft_schedule=e_queue_schedules[0], \
                 BE_schedule=e_queue_schedules[0]):

        # setup queues and their schedule
        self.ST_count = ST_count
        self.ST_schedule = ST_schedule
        self.emergency_count = emergency_count
        self.emergency_schedule = emergency_schedule
        self.sporadic_hard_count = sporadic_hard_count
        self.sporadic_hard_schedule = sporadic_hard_schedule
        self.sporadic_soft_count = sporadic_soft_count
        self.sporadic_soft_schedule = sporadic_soft_schedule
        self.BE_count = BE_count
        self.BE_schedule = BE_schedule

        # dont forget initial GCL is global
        global g_offline_GCL
        self.offline_GCL = g_offline_GCL  # does this even need to be stored here? Can just use global one?
        self.active_GCL = self.offline_GCL  # initially. Can be changed with modify_GCL()


    # changes the active GCL in some way
    def modify_GCL(self):
        pass


    # makes sure that the frame is set up correctly and passes the acceptance test
    def acceptance_test(self, frame):
        # dummy function
        return True


    def packet_ingress(self, packet):
        pass


    def packet_egress(self, packet):
        pass


    def to_string(self):
        out_str = ""

        # print queue types with some formatting
        out_str += "ST_Count: "+str(self.ST_count)
        out_str += "\nST_schedule: "+str(self.ST_schedule)
        out_str += "\nemergency_count: "+str(self.emergency_count)
        out_str += "\nemergency_schedule: "+str(self.emergency_schedule)
        out_str += "\nsporadic_hard_count: "+str(self.sporadic_hard_count)
        out_str += "\nsporadic_hard_schedule: "+str(self.sporadic_hard_schedule)
        out_str += "\nsporadic_soft_count: "+str(self.sporadic_soft_count)
        out_str += "\nsporadic_soft_schedule: "+str(self.sporadic_soft_schedule)
        out_str += "\nBE_count: "+str(self.BE_count)
        out_str += "\nBE_schedule: "+str(self.BE_schedule)

        # print offline_GCL
        out_str += "\nOffline_GCL:\n"
        for key in self.offline_GCL:
            out_str += str(key)+": "+str(self.offline_GCL[key])+"\n"  # if I end up using global just change this to global?

        # print active_GCL if it is different to offline_GCL
        if self.offline_GCL == self.active_GCL:
            out_str += "Active_GCL is identical to offline_GCL"
        else:
            out_str += "Active_GCL:\n"
            for key in self.active_GCL:
                out_str += str(key)+": "+str(self.active_GCL[key])+"\n"

        # return string
        return out_str




##################################################
############# INOUT PARSER FUNCTIONS #############
##################################################

## HELPERS
# main function to bulk parse all inputs from file paths defined under  ### USER SETTINGS ###
def bullk_parse(network_topo_file, queue_definition_file, GCL_file, traffic_definition_file):

    # network topo
    n_topo_return_value = network_topo_parse_wrapper(network_topo_file)
    if n_topo_return_value == 0:
        return 0

    # else if there is a filename change
    elif type(n_topo_return_value) is tuple:
        network_topo_file = n_topo_return_value[0]  # update current filename for routing table parse
        if n_topo_return_value[1] == 0:  # if it still failed
            return 0


    # routing table
    if routing_table_parse_wrapper(network_topo_file) == 0:
        return 0


    # GCL
    if GCL_parse_wrapper(GCL_file) == 0:
        return 0


    # queue definition
    if queue_def_parse_wrapper(queue_definition_file) == 0:
        return 0


    # traffic definition
    if traffic_parse_wrapper(traffic_definition_file) == 0:
        return 0


    # all success
    return 1



# helper function to recursively check switches are error free
def error_check_switch(switch):

    global g_node_id_dict  # for readability
    end_station_count = 0
    switch_count = 0
    child_nodes_count = len(switch)


    # check the switch itself for errors
    if len(switch.keys()) != 2:  # switch must only have 2 attributes called "name" and "unique_id"
        print("ERROR: A switch has too many attributes")
        return 0
    if( ("unique_id" not in switch.keys()) or ("name" not in switch.keys()) ):
        print("ERROR: Invalid switch attribute names")
        return 0
    if int(switch.get("unique_id")) in g_node_id_dict:  # make sure each ID is unique
        print("ERROR: Duplicate ID found (ID:", switch.get("unique_id")+")")
        return 0
    if child_nodes_count < 1:  # must be at least 1 other node connected to a switch
        print("ERROR: There must be at least 1 end station connected to switch (ID:", switch.get("unique_id")+")")
        return 0


    # check children for errors
    for node in switch:
        if( (node.tag != "Switch") and (node.tag != "End_Station") ):  # only switches or end stations can be children of switches
            print("ERROR: Invalid switch node tag connected to switch (ID:", switch.get("unique_id")+")")
            return 0

        # child end station
        if node.tag == "End_Station":  # check any end stations for errors
            if len(node.keys()) != 2:  # end stations must only have 2 attributes called "name" and "unique_id"
                print("ERROR: End Station has too many attributes")
                return 0
            if( ("unique_id" not in node.keys()) or ("name" not in node.keys()) ):
                print("ERROR: Invalid end station attribute names")
                return 0
            if int(node.get("unique_id")) in g_node_id_dict:  # make sure we dont have any duplicate IDs
                print("ERROR: Duplicate ID found (ID:", node.get("unique_id")+")")
                return 0
            if len(node) != 0:  # end stations are not allowed any children
                print("ERROR: End station (ID:", node.get("unique_id")+")", "has children")
                return 0
            if int(node.get("unique_id")) in g_node_id_dict:  # make sure each ID is unique
                print("ERROR: Duplicate ID found (ID:", switch.get("unique_id")+")")
                return 0
            end_station_count += 1  # no errors, add to count
            end_station_node = End_Station(int(node.get("unique_id")), switch.get("unique_id"), node.get("name"))  # create node
            g_node_id_dict[int(node.get("unique_id"))] = end_station_node  # add this erorr free end station to node list
        if end_station_count < 1:  # must be at least 1 end station
            print("ERROR: There must be at least 1 end station connected to switch (ID:", switch.get("unique_id")+")")
            return 0

        # child switch
        if node.tag == "Switch":
            if error_check_switch(node) == 0:  # recursively check for errors on this switch and its children switches if any
                return 0
            if int(node.get("unique_id")) in g_node_id_dict:  # double check none of its children has its ID before adding it
                print("ERROR: Duplicate ID found (ID:", node.get("unique_id")+")")
                return 0
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
        return 0
    if controller.tag != "Controller":  # controller must be called "Controller" at depth 1 in the XML
        print("ERROR: Controller missing or at incorrect depth")
        return 0
    if len(controller.keys()) != 2:  # controller must only have 2 attributes called "name" and "unique_id"
        print("ERROR: Controler has too many attributes")
        return 0
    if( ("unique_id" not in controller.keys()) or ("name" not in controller.keys()) ):
        print("ERROR: Invalid controller attribute names")
        return 0
    if controller.get("unique_id") != str(0):  # controller ID must be 0
        print("ERROR: Controller ID must be 0")
        return 0
    controller_node = Controller(0, controller.get("name"))  # create controller node with id 0 and name from file
    g_node_id_dict[0] = controller_node  # add controller to global node list


    ## Switches
    switch_count = len(root[0])
    if switch_count < 1:  # must be at least 1 switch
        print("ERROR: There must be at least 1 switch")
        return 0
    for switch in controller:
        if switch.tag != "Switch":  # make sure we only have switches and not end stations connected to the controller
            print("ERROR: Invalid switch node tag connected to the Controller")
            return 0
        if error_check_switch(switch) == 0:  # recursively check for errors on this switch and its children switches if any
            return 0
        if int(switch.get("unique_id")) in g_node_id_dict:  # double check none of its children has its ID before adding it
            print("ERROR: Duplicate ID found (ID:", switch.get("unique_id")+")")
            return 0
        switch_node = Switch(int(switch.get("unique_id")), switch.get("name"))  # create node
        g_node_id_dict[int(switch.get("unique_id"))] = switch_node  # switch and its children are error free, add its ID to list


    ### Finish up
    # check we havent exceeded the max count
    if len(g_node_id_dict) > MAX_NODE_COUNT:
        print("ERROR: Too many nodes:", len(g_node_id_dict), "(MAX:", str(MAX_NODE_COUNT)+")")
        return 0

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
            return 0

    # each switch should be present in the routing table
    if len(routing_table) != len(switch_list):
        print("ERROR: Incorrect amount of switches present in the global routing table")
        return 0


    # populate switch objects with their appropriate routing table
    for key in g_node_id_dict:
        if key in routing_table:
            if key == 0:  # add entire routing table to the controller
                g_node_id_dict[key].set_routing_table(routing_table)
                g_node_id_dict[key].set_local_routing_table(routing_table[key])

            else:  # only add local routing table to switches
                g_node_id_dict[key].set_local_routing_table(routing_table[key])

    return 1


# function to parse the queue definition file
def parse_queue_definition(f_queue_def, debug=0):

    global g_node_id_dict, e_queue_schedules, e_queue_type_names

    # parse XML file and get root
    parser = etree.XMLParser(ns_clean=True)
    tree = etree.parse(f_queue_def, parser)
    root = tree.getroot()

    # get a list of all switches present from the network topo
    switch_list = []
    for key in g_node_id_dict:
        if g_node_id_dict[key].node_type == "Switch":
            switch_list.append(key)
    switch_list.append(0)  # controller is also a switch


    ## Error checking and adding defaults
    if len(switch_list) != len(root):  # amount of switches present in the network should match the amount in the switch definition
        print("ERROR: Incorrect number of switches", "("+str(len(root)), "in queue definition vs", str(len(switch_list)), "in network)")
        return 0

    # check each switch in the file for errors
    queue_def_switches = []
    for switch in root:

        if int(switch.get("unique_id")) not in switch_list:  # each switch ID in file should be in the actual switch list parsed from the network topology
            print("ERROR: Unable to find switch", "("+"ID:", str(switch.get("unique_id"))+")", "from queue definition in the network")
            return 0
        if int(switch.get("unique_id")) in queue_def_switches:  # do not allow duplicate switch IDs
            print("ERROR: Found duplicate Switch ID:", str(switch.get("unique_id")))
            return 0
        else:  # if not diplicate then add the id to the list
            queue_def_switches.append(int(switch.get("unique_id")))
        if len(switch) != 1:  # switches should only have 1 child, the types of queue it holds
            print("ERROR: Switch (ID:", switch.get("unique_id")+") has incorrect number of children")
            return 0
        if switch[0].tag != "Queues":  # child should be called Queues
            print("ERROR: Incorrect child name for queue types in Switch (ID:", switch.get("unique_id")+")")
            return 0
        if len(switch[0]) != len(e_queue_type_names):  # each switch should contain all 5 types of queue
            print("ERROR: Queue type missing in Switch (ID:", switch.get("unique_id")+")")
            return 0

        # check each queue type in each switch for errors
        queue_count = 0
        queue_types_present = []
        for queue_type in switch[0]:

            if queue_type.tag not in e_queue_type_names:  # check the queue names match expected titles
                print("ERROR: Unrecognised queue name:", queue_type.tag)
                return 0
            if queue_type.tag in queue_types_present:  # do not allow duplicate queue type names
                print("ERROR: Found duplicate Queue type", "\""+str(queue_type.tag)+"\"", "in Switch (ID:", switch.get("unique_id")+")")
                return 0
            else:  # if not duplicate add the queue type to the temp list
                queue_types_present.append(queue_type.tag)

            if "count" not in queue_type.keys():  # every queue type must have at least a "count" attribute
                print("ERROR: Queue", "\""+str(queue_type.tag)+"\"", "in Switch (ID:", \
                      switch.get("unique_id")+")", "is missing \"count\" attribute")
                return 0
            if int(queue_type.get("count")) < 1:  # each queue type count attribute must be > 1 (cant have 0 of a queue)
                print("ERROR: Cant have a queue count less than 1 in queue", "\""+str(queue_type.tag)+"\"", \
                      "in Switch (ID:", switch.get("unique_id")+")")
                return 0
            queue_count += int(queue_type.get("count"))  # add count attribute to determine how many queues in this switch later on (max: 8)

            if "schedule" not in queue_type.keys():  # each queue should contain a 'schedule' attribute, if not it defaults to FIFO
                if debug:
                    print("Switch (ID:", switch.get("unique_id")+") has not defined queue schedule as required. Defaulting to FIFO")
                queue_type.set("schedule", e_queue_schedules[0])  # add schedule attribute to switch's queue type
            if queue_type.get("schedule") not in e_queue_schedules:  # make sure schedule attribute is valid
                print("ERROR: Unrecognised queue schedule for queue", "\""+str(queue_type.tag)+"\"", \
                      "in Switch (ID:", switch.get("unique_id")+")")
                return 0

        # final checks
        if queue_count > 8:  # cant be more than 8 queues per switch
            print("ERROR: Found more than 8 queues in Switch (ID:", switch.get("unique_id")+")")
            return 0
        if queue_count < 8:  # if all queues present but less than 8 defined, fill the difference with BE queues
            queues_needed = 8 - queue_count
            if debug:
                print("Switch (ID:", switch.get("unique_id")+") has not defined 8 queues as required.", \
                      "Adding", queues_needed, "Best Effort queue"+("s" if queues_needed != 1 else ""), "to make up the difference")

            for queue_type in switch[0]:
                if queue_type.tag == "BE":  # find the BE queue to error check
                    temp_count = int(queue_type.get("count"))
                    temp_count += queues_needed
                    queue_type.set("count", str(temp_count))  # set new count for BE queue


        # now populate the current switch with its error checked queue definition further errors kill the program
        ST_count, emergency_count, sporadic_hard_count, sporadic_soft_count, BE_count = [0, 0, 0, 0, 0]
        ST_schedule, emergency_schedule, sporadic_hard_schedule, sporadic_soft_schedule, BE_schedule = [0, 0, 0, 0, 0]

        for queue_type in switch[0]:
            if queue_type.tag == "ST":
                ST_count = int(queue_type.get("count"))
                ST_schedule = str(queue_type.get("schedule"))
            if queue_type.tag == "Emergency":
                emergency_count = int(queue_type.get("count"))
                emergency_schedule = str(queue_type.get("schedule"))
            if queue_type.tag == "Sporadic_Hard":
                sporadic_hard_count = int(queue_type.get("count"))
                sporadic_hard_schedule = str(queue_type.get("schedule"))
            if queue_type.tag == "Sporadic_Soft":
                sporadic_soft_count = int(queue_type.get("count"))
                sporadic_soft_schedule = str(queue_type.get("schedule"))
            if queue_type.tag == "BE":
                BE_count = int(queue_type.get("count"))
                BE_schedule = str(queue_type.get("schedule"))

        queue_def = Queue(ST_count, emergency_count, sporadic_hard_count, sporadic_soft_count, BE_count, \
                          ST_schedule, emergency_schedule, sporadic_hard_schedule, sporadic_soft_schedule, BE_schedule)
        g_node_id_dict[int(switch.get("unique_id"))].set_queue_def(queue_def)


    return 1  # done



# function to error check and parse the GCL
def parse_GCL(f_GCL):

    global g_offline_GCL

    # open gcl file
    f_GCL = Path(f_GCL)  # convert string filename to actual file object
    with f_GCL.open() as f:
        f_lines = f.read().splitlines()  # put entire file into an ordered list

        if( (f_lines[0][0:3] != "T0 ") and (f_lines[0][0:3] != "T0-T") ):  # first line should be T0
            print("ERROR: First line in GCL must start at timestamp T0")
            return 0
        if( (f_lines[-1][-7:] != " REPEAT") and (f_lines[-1][-7:] != " repeat") ):  # last line should contain REPEAT statement
            print("ERROR: Final line of GCL should be REPEAT")
            return 0


        # check each line for errors
        current_timestamp = -1  # initialise this and use it to make sure the list is sequential and we account for every range
        for line in f_lines:

            if line[0] != "T":  # all lines should start with T
                print("ERROR: Every line in the GCL must start with a T")
                return 0
            if "-" in line:  # groups should have both timestamps starting with T
                if( (line.split('-')[0][0] != "T") or (line.split('-')[1][0] != "T") ):
                    print("ERROR: In group timestamp", "\""+str(line.split(' ')[0])+"\"", "both sides should start with \"T\"")
                    return 0


            # if not the final line
            if line != f_lines[-1]:
                for index in range(1, 9):  # check final 8 positions for 0's and 1's
                    if( (line[-index] != "1") and (line[-index] != "0") ):
                        print("ERROR: GCL string must be made up of 0's and 1's at line", "\""+str(line)+"\"")
                        return 0
                if line[-9] != " ":  # make sure timestamps are seperated from the gate positions by spaces " "
                    print("ERROR: Timestamps must be followed by a space")
                    return 0


            # final error check (for sequential timestamps) AND add data to global GCL list here
            timing = line.split(' ')[0]  # split on space, LHS is timing data, RHS is gate state
            if "-" in timing:  # if we are dealing with a group of timestamps
                if current_timestamp+1 == int(timing.split('-')[0][1:]):  # if current timestamp +1 is the first value in the group in the GCL
                    # then this is sequential so add the range to the timestamp
                    group_size = int(timing.split('-')[1][1:]) - int(timing.split('-')[0][1:])  # get the size of the range
                    g_offline_GCL[current_timestamp+1] = line.split(' ')[1]  # add gate state to dict for start timestamp
                    current_timestamp += group_size+1
                else:
                    print("ERROR: Timestamp value at line", "\""+str(line)+"\"", "is not sequential")
                    return 0

            else:  # else it is a single timestamp
                if int(timing[1:]) == current_timestamp+1:  # if current timestamp+1 is the next timestamp in the GCL
                    # then this is sequential so increment the timestamp by 1 timestamp
                    current_timestamp += 1
                    g_offline_GCL[current_timestamp] = line.split(' ')[1]  # add gate state to dictionary for this timestamp
                else:
                    print("ERROR: Timestamp value at line", "\""+str(line)+"\"", "is not sequential")
                    return 0


    return 1



# function to error check and parse the traffic definiton file
def parse_traffic_definition(f_traffic_def, debug=0):

    global g_generic_traffics_list
    traffic_types = e_queue_type_names  # traffic can be same types as queue types

    # except we cant initialise the Emergency type traffic, ST -> Emergency is infered by the simulator itself
    traffic_types.remove("Emergency")


    # parse XML file and get root
    parser = etree.XMLParser(ns_clean=True)
    tree = etree.parse(f_traffic_def, parser)
    root = tree.getroot()


    ## error checks and object building
    if len(root) < 1:  # make sure there is at least 1 type of traffic
        print("ERROR: There must be at least 1 type of traffic defined")
        return 0

    traffic_ids = []  # used to keep track of all IDs to make sure there are no duplicates
    for child in root:  # error check and build dict per traffic type

        if child.tag != "Traffic":  # all traffic definitions must be tagged with "Traffic"
            print("ERROR: Invalid name found for child:", "\""+child.tag+"\". Must be \"Traffic\"")
            return 0
        if "unique_id" not in child.keys():  # each traffic definition must have at least 1 attribute called unique_id
            print("ERROR: Traffic definitions must have a \"unique_id\" attribute")
            return 0
        if int(child.get("unique_id")) in traffic_ids:  # each unique id must be unique
            print("ERROR: Found duplicate traffic ID:", child.get("unique_id"))
            return 0
        else:  # otherwise add it to the current ID list
            traffic_ids.append(int(child.get("unique_id")))
        if "name" not in child.keys():  # check for a name attribute
            if debug:
                print("Child ID:", child.get("unique_id"), "has no \"name\" attribute. Defaulting to \"unnamed\"")
            child.set("name", "unnamed")
        if "offset" not in child.keys():  # check for an offset attribute
            if debug:
                print("Child ID:", child.get("unique_id"), "has no \"offset\" attribute. Defaulting to \"0\"")
            child.set("offset", "0")
        if "destination_id" not in child.keys():  # check for a destination attribute
            if debug:
                print("Child ID:", child.get("unique_id"), "has no \"destination_id\" attribute. Defaulting to \"0\"")
            child.set("destination_id", "0")
        if child.get("destination_id") != "0":  # destination id should be the id of one of the end points or 0
            if int(child.get("destination_id")) not in g_node_id_dict:  # if its missing from all IDs fail
                print(child.get("destination_id"), "not in", g_node_id_dict)
                print("ERROR: Traffic (ID:", child.get("unique_id")+")", "has destination_id: \"" + \
                      str(child.get("destination_id"))+"\"", "which does not match an End Station")
                return 0
            if g_node_id_dict[int(child.get("destination_id"))].node_type != "End_Station":  # node must be end station
                print("ERROR: Traffic (ID:", child.get("unique_id")+")", "has destination_id: \"" + \
                      str(child.get("destination_id"))+"\"", "which does not match an End Station")
                return 0
        if len(child.keys()) != 4:  # traffic should only have 4 attributes. "unique_id", "name" "offset" and "destination_id"
            print("ERROR: Traffic (ID:", child.get("unique_id")+")", "has incorrect amount of attributes (should be 4)")
            return 0
        if len(child) != 1:  # traffic should only have 1 child, the type of traffic it is
            print("ERROR: Traffic (ID:", child.get("unique_id")+") has incorrect number of children")
            return 0

        # build dict entry
        traffic_type = {}
        traffic_type["offset"] = int(child.get("offset"))
        traffic_type["name"] = str(child.get("name"))
        traffic_type["destination_id"] = str(child.get("destination_id"))

        # deal with specific traffic types and prepare objects for the child
        if child[0].tag == traffic_types[0]:  # ST Traffic
            max_release_jitter = 0.0
            hard_deadline = 0.0
            period = 0.0

            if len(child[0].keys()) != 3:  # must have 3 attributes
                print("ERROR: Traffic (ID:", child.get("unique_id")+") type has incorrect number of attributes")
                return 0
            if "max_release_jitter" not in child[0].keys():  # max_release_jitter -> delay_jitter_constraints
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"max_release_jitter\" attribute")
                return 0
            else:
                max_release_jitter = float(child[0].get("max_release_jitter"))
            if "hard_deadline" not in child[0].keys():  # hard deadline
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"hard_deadline\" attribute")
                return 0
            else:
                hard_deadline = float(child[0].get("hard_deadline"))
            if "period" not in child[0].keys():  # period
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"period\" attribute")
                return 0
            else:
                period = float(child[0].get("period"))

            # start building dict
            traffic_type["max_release_jitter"] = float(max_release_jitter)
            traffic_type["hard_deadline"] = float(hard_deadline)
            traffic_type["period"] = float(period)
            traffic_type["type"] = str(traffic_types[0])


        elif child[0].tag == traffic_types[1]:  # Sporadic Hard
            max_release_jitter = 0.0
            hard_deadline = 0.0
            min_inter_release = 0.0  # if this remains 0 then we have aperiodic traffic

            if len(child[0].keys()) != 3:  # must have 3 attributes
                print("ERROR: Traffic (ID:", child.get("unique_id")+") type has incorrect number of attributes")
                return 0
            if "max_release_jitter" not in child[0].keys():  # max_release_jitter -> delay_jitter_constraints
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"max_release_jitter\" attribute")
                return 0
            else:
                max_release_jitter = float(child[0].get("max_release_jitter"))
            if "min_inter_release" not in child[0].keys():  # min_inter_release
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"min_inter_release\" attribute")
                return 0
            else:
                min_inter_release = float(child[0].get("min_inter_release"))
            if "hard_deadline" not in child[0].keys():  # hard deadline
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"hard_deadline\" attribute")
                return 0
            else:
                hard_deadline = float(child[0].get("hard_deadline"))

            # start building dict
            traffic_type["max_release_jitter"] = float(max_release_jitter)
            traffic_type["hard_deadline"] = float(hard_deadline)
            traffic_type["min_inter_release"] = float(min_inter_release)
            traffic_type["type"] = str(traffic_types[1])


        elif child[0].tag == traffic_types[2]:  # Sporadic Soft
            max_release_jitter = 0.0
            soft_deadline = 0.0
            min_inter_release = 0.0  # if this remains 0 then we have aperiodic traffic

            if len(child[0].keys()) != 3:  # must have 3 attributes
                print("ERROR: Traffic (ID:", child.get("unique_id")+") type has incorrect number of attributes")
                return 0
            if "max_release_jitter" not in child[0].keys():  # max_release_jitter -> delay_jitter_constraints
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"max_release_jitter\" attribute")
                return 0
            else:
                max_release_jitter = float(child[0].get("max_release_jitter"))
            if "min_inter_release" not in child[0].keys():  # min_inter_release
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"min_inter_release\" attribute")
                return 0
            else:
                min_inter_release = float(child[0].get("min_inter_release"))
            if "soft_deadline" not in child[0].keys():  # hard deadline
                print("ERROR: Traffic (ID:", child.get("unique_id")+") is missing \"soft_deadline\" attribute")
                return 0
            else:
                soft_deadline = float(child[0].get("soft_deadline"))

            # start building dict
            traffic_type["max_release_jitter"] = float(max_release_jitter)
            traffic_type["soft_deadline"] = float(soft_deadline)
            traffic_type["min_inter_release"] = float(min_inter_release)
            traffic_type["type"] = str(traffic_types[2])


        elif child[0].tag == traffic_types[3]:  # BE has no time limitations
            traffic_type["type"] = str(traffic_types[3])  # only need type for dict

        else:  # unrecognised
            print("ERROR: Traffic (ID:", child.get("unique_id")+") has invalid traffic type:", child[0].tag)
            return 0


        # continue building the dict and then add it to the global list of generic types
        g_generic_traffics_dict[child.get("unique_id")] = traffic_type

    return 1



## WRAPPERS
# network topo parser wrapper
def network_topo_parse_wrapper(network_topo_file):

    # parse network topo from given file
    f = Path(network_topo_file)
    if f.is_file():
        if(parse_network_topo(network_topo_file) == 0):  # file syntax error
            print("ERROR: In file:", "\""+network_topo_file+"\"")
            return 0
        else:
            print("Successfully parsed network topology file:", "\""+network_topo_file+"\"")
            return 1
    else:
        print("ERROR: Network topology not found:", "\""+network_topo_file+"\"")

        # see if the user wants to generate a new topology
        if gen_utils.get_YesNo_descision("Would you like to create a Network Topology?"):
            if gen_utils.get_YesNo_descision("Would you like to use the same name ("+str(network_topo_file)+")?"):  # keep same filename
                network_topo_gen.generate(network_topo_file, MAX_NODE_COUNT)  # call generator
                return network_topo_parse_wrapper(network_topo_file)  # re-parse

            else:  # generate new topo with different filename
                new_filename = "simulator_files\\"
                new_filename += gen_utils.get_str_descision("Enter a filename for the Network Topology (do NOT include .xml)", \
                                                            restricted_only=True)
                new_filename += ".xml"
                print("Accepted filename:", new_filename)
                network_topo_gen.generate(new_filename, max_nodes=MAX_NODE_COUNT)  # call generator
                return (new_filename, network_topo_parse_wrapper(new_filename))  # re-parse and return new filename for routing table parse

        # see if the user wants to search for a different filename
        elif gen_utils.get_YesNo_descision("Would you like to look for a different Topology filename?"):
            new_filename = "simulator_files\\"
            new_filename += gen_utils.get_str_descision("Enter a filename for the Network Topology (do NOT include .xml)", \
                                                        restricted_only=True)
            new_filename += ".xml"
            print("Trying filename: \""+new_filename+"\"")
            return (new_filename, network_topo_parse_wrapper(new_filename))

        # if no new file generated and the user doesnt want to search for one then
        print("ERROR: Cannot run simulator without a valid network topology")
        return 0



# routing table parser wrapper
def routing_table_parse_wrapper(network_topo_file):

    # parse routing table from the network topology file
    f = Path(network_topo_file)
    if f.is_file():
        if(parse_routing_table(network_topo_file) == 0):  # file syntax error
            print("ERROR: In file:", "\""+network_topo_file+"\"")
            return 0
        else:
            print("Successfully parsed routing table from file:", "\""+network_topo_file+"\"")
            return 1
    else:
        print("ERROR: Network topology file not found:", "\""+network_topo_file+"\". Unable to parse routing table")
        return 0



# GCL parser wrapper
def GCL_parse_wrapper(GCL_file):

    f = Path(GCL_file)
    if f.is_file():
        if parse_GCL(GCL_file) == 0:  # file syntax error
            print("ERROR: In file:", "\""+GCL_file+"\"")
            return 0
        else:
            print("Successfully parsed GCL file:", "\""+GCL_file+"\"")
            return 1
    else:
        print("ERROR: GCL not found:", "\""+GCL_file+"\"")

        # see if the user wants to search for another file
        if gen_utils.get_YesNo_descision("Would you like to look for a different GCL filename?"):
            new_filename = "simulator_files\\"
            new_filename += gen_utils.get_str_descision("Enter a filename for the GCL (DO include file extension)", \
                                                        restricted_only=True)
            print("Trying filename: \""+new_filename+"\"")
            return GCL_parse_wrapper(new_filename)

        # else
        print("ERROR: Cannot run simulator without a valid GCL file")
        return 0



# queue definition parser wrapper
def queue_def_parse_wrapper(queue_definition_file):

    # parse queue definition from its xml file
    f = Path(queue_definition_file)
    if f.is_file():
        if parse_queue_definition(queue_definition_file) == 0:  # syntax error
            print("ERROR: In file:", "\""+queue_definition_file+"\"")
            return 0
        else:
            print("Successfully parsed queue definition file:", "\""+queue_definition_file+"\"")
            return 1
    else:
        print("ERROR: Queue Definition not found:", "\""+queue_definition_file+"\"")

        if gen_utils.get_YesNo_descision("Would you like to create a new Queue Definition?"):

            # see if user wants to change the filename
            new_filename_in_use = False
            new_filename = ""
            if gen_utils.get_YesNo_descision("Would you like to use the current filename ("+queue_definition_file+")?"):
                new_filename_in_use = False  # do nothing so we can use the same filename
            else:  # get new filename
                new_filename_in_use = True
                new_filename = "simulator_files\\"
                new_filename += gen_utils.get_str_descision("Enter a filename for the Queue Definition file (do NOT include .xml)", \
                                                            restricted_only=True)
                new_filename += ".xml"
                print("Accepted filename:", new_filename)


            # see if the user wants to use the current switch ID list from the network topo for simplicity
            if gen_utils.get_YesNo_descision("Would you like to use the current switch IDs from the Network Topology?"):

                # get list of controller and switch IDs into a list()
                id_list_to_send = []
                for key in g_node_id_dict:
                    if g_node_id_dict[key].node_type != "End_Station":
                        id_list_to_send.append(key)

                if new_filename_in_use:  # call queue def generator with new filename and current IDs and try to reparse
                    queue_def_gen.generate(new_filename, MAX_NODE_COUNT, id_list_to_send, e_queue_schedules)
                    return queue_def_parse_wrapper(new_filename)
                else:  # call queue def generator with old filename and current IDs and try to reparse
                    queue_def_gen.generate(queue_definition_file, MAX_NODE_COUNT, id_list_to_send, e_queue_schedules)
                    return queue_def_parse_wrapper(queue_definition_file)


            else:
                if new_filename_in_use:  # call queue def generator with new filename and no IDs and try to reparse
                    queue_def_gen.generate(new_filename, MAX_NODE_COUNT, allowed_schedules=e_queue_schedules)
                    return queue_def_parse_wrapper(new_filename)
                else:  # call queue def generator with old filename and no IDs and try to reparse
                    queue_def_gen.generate(queue_definition_file, MAX_NODE_COUNT, allowed_schedules=e_queue_schedules)
                    return queue_def_parse_wrapper(queue_definition_file)


        # if user doesnt want to create a new one - see if they want to search for a different one
        elif gen_utils.get_YesNo_descision("Would you like to look for a different Queue Definition filename?"):
            new_filename = "simulator_files\\"
            new_filename += gen_utils.get_str_descision("Enter a filename for the Queue Definition (do NOT include .xml)", \
                                                        restricted_only=True)
            new_filename += ".xml"
            print("Trying filename: \""+new_filename+"\"")
            return queue_def_parse_wrapper(new_filename)  # dont need to return the new filename as nothing else needs it

        # if no new definition generated and the user doesnt want to search for one then:
        print("ERROR: Cannot run simulator without a valid Queue Definition file")
        return 0



# GCL parser wrapper
def traffic_parse_wrapper(traffic_definition_file):

    # parse the generic types of traffic our simulator will be able to send
    f = Path(traffic_definition_file)
    if f.is_file():
        if parse_traffic_definition(traffic_definition_file) == 0:  # syntax error
            print("ERROR: In file:", "\""+traffic_definition_file+"\"")
            return 0
        else:
            print("Successfully parsed traffic definition file:", "\""+traffic_definition_file+"\"")
            return 1
    else:
        print("ERROR: Traffic definition not found:", "\""+traffic_definition_file+"\"")

        # see if user wants to create a new file
        if gen_utils.get_YesNo_descision("Would you like to create a new Traffic Definition?"):

            # see if user wants to change the filename
            if gen_utils.get_YesNo_descision("Would you like to use the current filename ("+traffic_definition_file+")?"):
                traffic_def_gen.generate(traffic_definition_file)  # generate
                return traffic_parse_wrapper(traffic_definition_file)  # attempt to re-parse

            else:  # get new filename
                new_filename = "simulator_files\\"
                new_filename += gen_utils.get_str_descision("Enter a filename for the Queue Definition file (do NOT include .xml)", \
                                                            restricted_only=True)
                new_filename += ".xml"
                print("Accepted filename:", new_filename)

                traffic_def_gen.generate(new_filename)  # generate
                return traffic_parse_wrapper(new_filename)  # attempt to re-parse


        # if user doesnt want to create a new one - see if they want to search for a different one
        elif gen_utils.get_YesNo_descision("Would you like to look for a different Traffic Definition filename?"):
            new_filename = "simulator_files\\"
            new_filename += gen_utils.get_str_descision("Enter a filename for the Traffic Definition (do NOT include .xml)", \
                                                        restricted_only=True)
            new_filename += ".xml"
            print("Trying filename: \""+new_filename+"\"")
            return traffic_parse_wrapper(new_filename)  # dont need to return the new filename as nothing else needs it


        # else
        print("ERROR: Cannot run simulator without a valid Traffic Definition file")
        return 0




##################################################
################# SIMULATOR CODE #################
##################################################

# parse files
if bullk_parse(network_topo_file, queue_definition_file, GCL_file, traffic_definition_file) == 0:
    print("CRITICAL ERROR: Failed to parse files")
    exit()
print()


## Set up end stations
# display traffic types, id and destination
print("Available Traffic types from the Traffic Definition File and their ID:")
print([("ID: "+str(key_id), "Type: "+str(g_generic_traffics_dict[key_id]["type"]), \
        "Dest: "+str(g_generic_traffics_dict[key_id]["destination_id"])) \
       for key_id in g_generic_traffics_dict])

# ask user which end station gets which traffic ruleset
traffic_ids = [id for id in g_generic_traffics_dict]  # get list of just the ID
es_ids = []
switch_ids = []
for node_id in g_node_id_dict:
    if g_node_id_dict[node_id].node_type == "End_Station":  # get end station from global id list
        t_id = gen_utils.get_restricted_descision("What generic Traffic ID should End_Station (ID: "+str(node_id)+")"+" get?", traffic_ids)
        if g_node_id_dict[node_id].set_traffic_rules(g_generic_traffics_dict[t_id])  == 0:
            exit()  # if failure
        es_ids.append(node_id)
    else:
        switch_ids.append(node_id)  # if not ES then node is Switch


## Begin Simulator
# timestamp initialised at 0 at top of file
max_timestamp = 28  # TODO : ask the user here when finished debugging using gen_utils.getInt...
for tick in range(1, max_timestamp):
    #print("Tick", tick)

    # first set GCL to timestamp
    if g_timestamp in g_offline_GCL:  # if time is present, update state, else we are in a range so leave it
        # TODO : somehow incorperate active GCL into this unless that is just for emergency queue
        g_current_GCL_state = g_offline_GCL[g_timestamp]


    # check each ES for traffic to send based on its traffic sending rules
    for es in es_ids:
        g_node_id_dict[es].check_to_generate()

    # ingress packets from every queue
    for switch in switch_ids:
        g_node_id_dict[switch].ingress_packets()

    # cycle the inner queues of every switch
    for switch in switch_ids:
        g_node_id_dict[switch].cycle_queues()

    # send packets from egress section of every queue
    for switch in switch_ids:
        g_node_id_dict[switch].egress_packets()

    # send packets in end station egress queues and digest any packets that are in the ingress queue
    for es in es_ids:
        g_node_id_dict[es].flush_egress()
        g_node_id_dict[es].digest_packets()


    g_timestamp += 1
    #print()

print()
print("Packets transmitted per Switch:")
for sw in switch_ids:
    print("SW ID:", sw, "packets transmitted:", g_node_id_dict[sw].packets_transmitted)
print()
print("Packet Latencies:\n ", g_packet_latencies)
print("Average="+str(sum(g_packet_latencies)/len(g_packet_latencies)))
print()
print("Average Queue Delays per Switch:")
for sw in switch_ids:
    print("SW ID:", sw, "average packet queueing delay:", g_node_id_dict[sw].average_queue_delay)
print()
print("Global packet delays:")
print(g_queueing_delays)




##################################################
################### DEBUG CODE ###################
##################################################






##################################################
################### DEMO  CODE ###################
##################################################

if 0:
    print()
    print("DEMO CODE AS FOLLOWS:")
    print()

    # print traffic types
    print("Defined Traffic types from XML (differentiated by \"unique_id\"):")
    for traffic in g_generic_traffics_list:
        print(traffic)
    print()

    # print nodes
    print("Nodes from XML:")
    for node in g_node_id_dict:
        print(g_node_id_dict[node].to_string())
    print()


    # # print GCL
    # print("GCL from file:")
    # for timestamp in g_offline_GCL:
    #    print(timestamp, g_offline_GCL[timestamp])
    # print()

    # print an example queue type
    print("Queue definition for Switch ID 0:")
    print(g_node_id_dict[0].queue_definition.to_string())
    print()

    # print routing table
    print("Routing table parsed from network topology:")
    for switch_node in g_node_id_dict[0].routing_table:
        print(switch_node, g_node_id_dict[0].routing_table[switch_node])
    print()
