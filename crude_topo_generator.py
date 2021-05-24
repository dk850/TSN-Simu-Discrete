"""
Command line interface to generate the network topology xml by stating everything manually over cli

No visualisation
"""
##################################################
##################### IMPORT #####################
##################################################

from lxml import etree
import generator_utilities as gen_utils




##################################################
################## GEN  WRAPPER ##################
##################################################

# wrapper to call generator class for use outside of this script
def generate(filename, max_nodes=0, allow_naming=True):

    # if max_nodes not set (or incorrectly set) by function, ask the user for an amount
    if max_nodes < 2:
        # must be more than 3 nodes due to there needing to be at least 1 of (controller & switch & end_station)
        max_nodes = gen_utils.get_int_descision("What is the maximum number of nodes?", 3, 100)


    # if allow_naming not set by function, ask the user if they want to name their nodes
    if allow_naming:
        node_name_mode = gen_utils.get_YesNo_descision("Do you wish to name your nodes?")
    else:
        node_name_mode = False


    # begin generation
    Generator(filename, max_nodes, node_name_mode)




##################################################
################ GENERATOR OBJECT ################
##################################################

class Generator():

    def __init__(self, filename, max_nodes, naming_mode):

        # setup object variables
        self.MAX_NODES = max_nodes
        self.naming_mode = naming_mode
        self.node_count = 0
        self.reserved_node_count = 0


        ### DEFINE  CONTROLLER
        controller_id = 0  # controller should always be ID 0

        # check if we want to name the controller
        if self.naming_mode:
            controller_name = gen_utils.get_str_descision("Input Controller name", alnum_only=True)
            print("Controller name set to:", "\""+controller_name+"\"", "successfully")
        else:
            controller_name = "unnamed"


        # set up the XML tree
        output_xml = etree.Element("Topology_Root")  # default root node
        etree.SubElement(output_xml, "Controller")  # add controller child under the root

        # apply attributes to controller child
        output_xml[0].set("unique_id", str(controller_id))
        output_xml[0].set("name", str(controller_name))


        ### DEFINE ROOT SWITCH(ES)
        while 1:
            self.reserved_node_count = 2  # reserve position for at least 1 switch and 1 end station
            max_new_nodes = self.MAX_NODES - self.reserved_node_count
            root_switches_count = gen_utils.get_int_descision("How many switches are connected directly to the controller?", \
                                                              1, max_new_nodes)

            # each root switch needs minimum 2 nodes (one for the switch and one for an end point) so need to re-check the amount here
            if root_switches_count > 1:
                self.reserved_node_count = root_switches_count * 2
                max_new_nodes = self.MAX_NODES - (self.reserved_node_count + 1)  # recalculate nodes needed (including controller)
                if max_new_nodes >= 0:  # leave while loop if we have enough room
                    break
                else:
                    print(root_switches_count, "switches is too many for the defined MAX_NODES ("+str(self.MAX_NODES)+")\n")
            else:  # only need to check of there is more than 1 base switch
                break

        print("Continuing with", str(root_switches_count), "root switches")


        # create child switch(es) under the controller node (0) in the root of the xml
        # we cant use build_switch(controller) here as end stations cant be connected directly to the controller
        for switch in range(1, int(root_switches_count)+1):  # 1-based

            # create switch node with unique ID
            etree.SubElement(output_xml[0], "Switch")
            output_xml[0][switch-1].set("unique_id", str(switch))

            # check if we need to name the node
            if self.naming_mode:
                sw_name = gen_utils.get_str_descision("Input name for switch "+str(switch), alnum_only=True)
            else:
                sw_name = "unnamed"
            output_xml[0][switch-1].set("name", sw_name)

        self.node_count = int(root_switches_count) + 1  # global variable of total number of nodes so far, 1-based (inc. controller)
        self.reserved_node_count -= int(root_switches_count)  # switches have been added to the node count so they are no longer needed to be reserved


        ### DEFINE CHILD SWITCHES AND END STATIONS
        # finaly, loop over all these root switches to create their children
        for rs in range(int(root_switches_count)):  # 0-based
            self.recur_build_switch(output_xml[0][rs])


        self.output(filename, output_xml)



    # recursive helper function to define any child end stations, switches and their names (if applicable)
    #  if any switches defined, then this is recursively called
    def recur_build_switch(self, root_node):

        ### END STATIONS
        # error checking
        if self.MAX_NODES - self.node_count == 0:
            print("ERROR: Invalid node count. Could not add further Switch or End Station")
            return -1

        # get number of end stations
        es_count = gen_utils.get_int_descision("How many end stations are connected to this switch (id: " + \
                                               str(root_node.get("unique_id"))+")?", 1, \
                                               (self.MAX_NODES - self.node_count - (self.reserved_node_count-1)) )

        # we need to loop es_count amount of times to add that many end stations
        for es in range(1, int(es_count)+1):  # 1-based

            if self.naming_mode:  # check if we are in naming mode
                es_name = gen_utils.get_str_descision("Input end station "+str(es)+" name", alnum_only=True)
            else:
                es_name = "unnamed"

            # add end station and its attributes to root node
            end_station = etree.SubElement(root_node, "End_Station")
            end_station.set("unique_id", str(self.node_count))  # unique id is at current global node count
            end_station.set("name", es_name)
            self.node_count += 1

        self.reserved_node_count -= 1  # one of those added end stations was a part of the minimum reserved


        ### CHILD SWITCHES
        # only allow addition of more switches if we havent/wont reach the maximum amount nodes
        while 1:
            if self.MAX_NODES - self.node_count - self.reserved_node_count < 2:  # need to have 2 or more free node spaces to accept another switch
                sw_count = 0
                break
            else:
                nodes_needed = self.MAX_NODES - self.node_count - self.reserved_node_count
                sw_count = gen_utils.get_int_descision("How many switches connected from this switch (id: " + \
                                                       str(root_node.get("unique_id"))+")?", 0, nodes_needed)

            # each switch needs minimum 2 nodes (one for the switch and one for an end point) so need to re-check the amount here
            if sw_count != 0:
                nodes_needed -= 2*sw_count

                # leave while loop if we have enough room
                if nodes_needed >= 0:
                    self.reserved_node_count += 2*sw_count  # if accepted add these as reserved nodes
                    break
                else:
                    print(sw_count, "switches is too many for the defined MAX_NODES ("+str(self.MAX_NODES)+")\n")
            else:
                break  # no change if no switches added


        # loop over all possible child switches and add their children (if 0 this will not be executed)
        for sw in range(1, int(sw_count)+1):  # 1-based

            # check if we are in naming mode
            if self.naming_mode:
                sw_name = gen_utils.get_str_descision("Input child switch "+str(sw)+" name", alnum_only=True)
            else:
                sw_name = "unnamed"

            # add child switch to this tree and then call this function again to determine its children/end stations
            switch = etree.SubElement(root_node, "Switch")
            switch.set("unique_id", str(self.node_count))  # unique id is at current global node count
            switch.set("name", sw_name)

            self.node_count += 1
            self.reserved_node_count -= 1

            self.recur_build_switch(switch)

        return 1



    def output(self, filename, out_xml):

        ### OUTPUT
        # print to console nicely
        print("\n\nFINAL NODE XML:\n" + etree.tostring(out_xml, pretty_print=True).decode() )

        # pipe to file
        with open(filename, "wb") as f:
            out = etree.ElementTree(out_xml)
            out.write(f, pretty_print=True)




##################################################
################### FOR  DEBUG ###################
##################################################

# fn = "simulator_files\\M_network_topology.xml"
# generate(fn)
