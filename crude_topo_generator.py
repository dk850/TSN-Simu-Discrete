"""
Command line interface to generate the network topology.xml by stating everything manually over cli

No visualisation
"""
# TODO : fix maximum node count - can be overran, doesnt fully account for future nodes on switches

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
        descision = input(prompt_question + "(Y/N) ")

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
    global g_node_count  # to show this is a dynamic variable


    ### END STATIONS
    es_count = get_int_descision("How many end stations are connected to this switch (id: " + \
                                 str(root_node.get("unique_id"))+")?", 1, (MAX_NODES-g_node_count))


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
        g_node_count += 1
        end_station.set("name", es_name)



    ### CHILD SWITCHES
    sw_count = get_int_descision("How many switches connected from this switch (id: " + \
                                 str(root_node.get("unique_id"))+")?", 0, (MAX_NODES-g_node_count))


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
        g_node_count += 1
        switch.set("name", sw_name)

        build_switch(switch)




##################################################
################# USER  SETTINGS #################
##################################################

# must be more than 3 nodes due to there needing to be at least 1 of {controller, switch, end station}
MAX_NODES = int(get_int_descision("What is the maximum number of nodes?", 3, 100))

# if the user wants to name their nodes we must give them extra prompts else we called them "unnamed"
node_name_mode = get_YesNo_descision("Do you wish to name your nodes?")




##################################################
############### DEFINE  CONTROLLER ###############
##################################################

controller_id = 0  # controller will always be ID 0

# check if we want to name the controller
if node_name_mode:
    controller_name = get_alphanumeric_descision("Input Controller name:")
    print("Controller name set to:", "\""+controller_name+"\"", "successfully")
else:
    controller_name = "unnamed"


# set up the XML
output_xml = etree.Element("Topology_Root")  # default root node
etree.SubElement(output_xml, "Controller")  # add controller child under the root

# apply attributes to controller child
output_xml[0].set("unique_id", str(controller_id))
output_xml[0].set("name", str(controller_name))




##################################################
############# DEFINE ROOT SWITCH(ES) #############
##################################################

# count must be more than 1 (must have at least 1 switch)
# and less than MAX_NODES-2 (as we already have 1 controller, and need at least 1 end station)
root_switches_count = get_int_descision("Input the amount of switches connected directly to the controller:", 1, MAX_NODES-2)
print("Continuing with", str(root_switches_count), "root switches")


# create child switch(es) under the controller node (0) in the root of the xml
# we cant use build_switch(controller) here as end stations cant be connected directly to the controller????????
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

g_node_count = int(root_switches_count) + 1  # global variable of total number of nodes so far, 1-based




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
print("\n\nFINAL NODE XML:\n"+etree.tostring(output_xml, pretty_print=True).decode())

# pipe to file
with open("network_topology.xml", "wb") as f:
    out = etree.ElementTree(output_xml)
    out.write(f, pretty_print=True)
