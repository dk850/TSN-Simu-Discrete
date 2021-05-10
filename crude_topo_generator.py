"""
Command line interface to generate the network topology.xml by stating everything manually over cli

No visualisation
"""
##################################################
##################### IMPORT #####################
##################################################

from lxml import etree




##################################################
################ HELPER FUNCTIONS ################
##################################################

# Helper function to ask the user a question and get a YES (True) or NO (False) answer
def get_YesNo_descision(prompt_question):
    final_descision = "loop"

    # ask the user the text given in function until a "Y" or "N" es entered
    while final_descision == "loop":
        descision = input(prompt_question + "(Y/N): ")

        if (descision == "Y") or (descision == "y"):
            final_descision = True
        elif (descision == "N") or (descision == "n"):
            final_descision = False
        else:
            print("\""+descision+"\"", "unrecognised (only Y or N accepted)")

    return final_descision



# Helper function to ask the user a question and return an integer value with optional equality constraints
def get_int_descision(prompt_question, min_int=-99999999, max_int=+99999999):
    final_count = "temp"

    # max int cant be smaller than min int
    if max_int < min_int:
        print("ERROR: max_int cant be smaller than min_int in function get_int_descision", max_int, min_int)
        exit()


    # make sure the user has selected an integer for us to return
    while not final_count.isdigit():
        final_count = input(prompt_question+" ")

        if final_count.isdigit():
            # Integer must obey equality constraints
            if min_int <= int(final_count) <= max_int:
                break
            else:
                print("Please try again with an integer between", str(min_int), "and", str(max_int), "\n")
                final_count = "temp"
        else:
            print("\""+final_count+"\"", "is not an integer")

    return final_count



# Helper function to return an alphanumeric string (not allowed special characters) optional testing for only alpha strings
def get_alphanumeric_descision(prompt_question, alpha_only=False):
    final_answer = "@false@"

    # Determine mode
    if alpha_only:
        while not final_answer.isalpha():
            final_answer = input(prompt_question+" ")

            if final_answer.isalpha():
                break
            else:
                print("\""+final_answer+"\"", "is not an alphabetic string (no spaces or numbers allowed)")

    # Else alphanumeric
    else:
        while not final_answer.isalnum():
            final_answer = input(prompt_question+" ")

            if final_answer.isalnum():
                break
            else:
                print("\""+final_answer+"\"", "is not an alphanumeric string (no spaces or special characters allowed)")

    return final_answer




##################################################
################# MAIN FUNCTIONS #################
##################################################

# function to define any child end stations, switches and their names (if applicable)
def build_switch(root_node):
    global g_node_count, g_reserved_node_count  # to show these are dynamic, global variables


    ### END STATIONS
    # error checking
    if MAX_NODES - g_node_count == 0:
        print("ERROR: Invalid node count. Could not add further Switch or End Station")
        exit()

    # get number of end stations
    es_count = int(get_int_descision("How many end stations are connected to this switch (id: " + \
                                     str(root_node.get("unique_id"))+")?", 1, (MAX_NODES - g_node_count - (g_reserved_node_count-1)) ))

    # we need to loop es_count amount of times to add that many end stations
    for es in range(1, int(es_count)+1):  # 1-based

        # check if we are in naming mode
        if node_name_mode:
            es_name = get_alphanumeric_descision("Input end station "+str(es)+" name:")
        else:
            es_name = "unnamed"

        # add end station and its attributes to root node
        end_station = etree.SubElement(root_node, "End_Station")
        end_station.set("unique_id", str(g_node_count))  # unique id is at current global node count
        end_station.set("name", es_name)
        g_node_count += 1

    g_reserved_node_count -= 1  # one of those added end stations was a part of the minimum reserved


    ### CHILD SWITCHES
    # only allow addition of more switches if we havent/wont reach the maximum amount nodes
    while 1:
        if MAX_NODES - g_node_count - g_reserved_node_count < 2:  # need to have 2 or more free node spaces to accept another switch
            sw_count = 0
            break
        else:
            nodes_needed = MAX_NODES - g_node_count - g_reserved_node_count
            sw_count = int(get_int_descision("How many switches connected from this switch (id: " + \
                                             str(root_node.get("unique_id"))+")?", 0, nodes_needed))

        # each switch needs minimum 2 nodes (one for the switch and one for an end point) so need to re-check the amount here
        if sw_count != 0:
            nodes_needed -= 2*sw_count

            # leave while loop if we have enough room
            if nodes_needed >= 0:
                g_reserved_node_count += 2*sw_count  # if accepted add these as reserved nodes
                break
            else:
                print(sw_count, "switches is too many for the defined MAX_NODES. Try agagin with a lower amount")
        else:
            break  # no change if no switches added

    # loop over all possible child switches and add their children (if 0 this will not be executed)
    for sw in range(1, int(sw_count)+1):  # 1-based

        # check if we are in naming mode
        if node_name_mode:
            sw_name = get_alphanumeric_descision("Input child switch "+str(sw)+" name:")
        else:
            sw_name = "unnamed"

        # add child switch to this tree and then call this function again to determine its children/end stations
        switch = etree.SubElement(root_node, "Switch")
        switch.set("unique_id", str(g_node_count))  # unique id is at current global node count
        switch.set("name", sw_name)

        g_node_count += 1
        g_reserved_node_count -= 1

        build_switch(switch)




##################################################
################# USER  SETTINGS #################
##################################################

# must be more than 3 nodes due to there needing to be at least 1 of (controller & switch & end_station)
MAX_NODES = int(get_int_descision("What is the maximum number of nodes?", 3, 100))

# if the user wants to name their nodes we must give them extra prompts else we called them "unnamed"
allow_naming = True  # manual override

if allow_naming:
    node_name_mode = get_YesNo_descision("Do you wish to name your nodes?")
else:
    node_name_mode = False




##################################################
############### DEFINE  CONTROLLER ###############
##################################################

controller_id = 0  # controller should always be ID 0

# check if we want to name the controller
if node_name_mode:
    controller_name = get_alphanumeric_descision("Input Controller name:")
    print("Controller name set to:", "\""+controller_name+"\"", "successfully")
else:
    controller_name = "unnamed"


# set up the XML tree
output_xml = etree.Element("Topology_Root")  # default root node
etree.SubElement(output_xml, "Controller")  # add controller child under the root

# apply attributes to controller child
output_xml[0].set("unique_id", str(controller_id))
output_xml[0].set("name", str(controller_name))




##################################################
############# DEFINE ROOT SWITCH(ES) #############
##################################################

while 1:
    g_reserved_node_count = 2  # reserve position for at least 1 switch and 1 end station
    max_new_nodes = MAX_NODES - g_reserved_node_count
    root_switches_count = int(get_int_descision("Input the amount of switches connected directly to the controller:", 1, max_new_nodes))

    # each root switch needs minimum 2 nodes (one for the switch and one for an end point) so need to re-check the amount here
    if root_switches_count > 1:
        g_reserved_node_count = root_switches_count * 2
        max_new_nodes = MAX_NODES - (g_reserved_node_count + 1)  # recalculate nodes needed (including controller)

        # leave while loop if we have enough room
        if max_new_nodes >= 0:
            break
        else:
            print(root_switches_count, "switches is too many for the defined MAX_NODES. Try again with a lower amount")

    # only need to check of there is more than 1 base switch
    else:
        break

print("Continuing with", str(root_switches_count), "root switches")


# create child switch(es) under the controller node (0) in the root of the xml
# we cant use build_switch(controller) here as end stations cant be connected directly to the controller
for switch in range(1, int(root_switches_count)+1):  # 1-based

    # create switch node with unique ID
    etree.SubElement(output_xml[0], "Switch")
    output_xml[0][switch-1].set("unique_id", str(switch))

    # check if we need to name the node
    if node_name_mode:
        sw_name = get_alphanumeric_descision("Input name for switch "+str(switch)+":")
    else:
        sw_name = "unnamed"
    output_xml[0][switch-1].set("name", sw_name)

g_node_count = int(root_switches_count) + 1  # global variable of total number of nodes so far, 1-based (inc. controller)
g_reserved_node_count -= int(root_switches_count)  # switches have been added to the node count so they are no longer needed to be reserved




##################################################
##### DEFINE CHILD SWITCHES AND END STATIONS #####
##################################################

# finaly, loop over all these root switches to create their children
for rs in range(int(root_switches_count)):  # 0-based
    build_switch(output_xml[0][rs])




##################################################
##################### OUTPUT #####################
##################################################

# print to console nicely
print("\n\nFINAL NODE XML:\n" + etree.tostring(output_xml, pretty_print=True).decode() )

# pipe to file
with open("network_topology.xml", "wb") as f:
    out = etree.ElementTree(output_xml)
    out.write(f, pretty_print=True)
