"""
Command line interface to generate the traffic definition xml by stating everything manually over cli

No visualisation
"""

##################################################
##################### IMPORT #####################
##################################################

from lxml import etree
import random
import generator_utilities as gen_utils




##################################################
################## GEN  WRAPPER ##################
##################################################

# wrapper to call generator class for use outside of this script
def generate(filename, allow_naming=True, allow_offset=True, allow_dest=True, allow_size=True):

    # if allow_naming allowed (Default), ask the user if they want to name their nodes
    if allow_naming:
        node_name_mode = gen_utils.get_YesNo_descision("Do you wish to name your traffic definitions? (Else they will default to \"unnamed\")")
    else:
        node_name_mode = False

    # if allow_offset allowed (Default), ask the user if they want to be able to change their offsets from 0
    if allow_offset:
        offset_set_mode = gen_utils.get_YesNo_descision("Do you wish to be able to change the offsets of any Traffics about to be defined?"\
                                                        + " (Else it will default to 0)")
    else:
        offset_set_mode = False

    # if allow_dest allowed (Default), ask the user if they want to be able to statically set destinations
    if allow_dest:
        dest_set_mode = gen_utils.get_YesNo_descision("Do you wish to be able to set the destinations of any Traffics about to be defined?"\
                                                      + " (Else it will default to a random End Station)")
    else:
        dest_set_mode = False

    # if allow_size allowed (Default), ask the user if they want to be able to individually set packet size
    if allow_size:
        size_set_mode = gen_utils.get_YesNo_descision("Do you wish to be able to set the packet size of any Traffics about to be defined?"\
                                                      + " (Else it will default to 16 Bytes)")
    else:
        size_set_mode = False

    # begin generation
    Generator(filename, node_name_mode, offset_set_mode, dest_set_mode, size_set_mode)




##################################################
################ GENERATOR OBJECT ################
##################################################

class Generator():

    def __init__(self, filename, node_name_mode, offset_set_mode, dest_set_mode, size_set_mode):

        queue_types = ["ST", "Sporadic_Hard", "Sporadic_Soft", "BE"]  # possible queue types for later

        # setup the XML tree
        output_xml = etree.Element("Traffic_Definition_Root")  # default root node

        # get amount of traffic types (at least 1)
        traffics_count = gen_utils.get_int_descision("How many generic Traffic Definitions would you like to create?", 1)


        # loop for all types the user wants to define
        traffics_ids = []
        for traffic in range(traffics_count):

            ## build base element stuff
            # create the Traffic XML element
            t_ele = etree.SubElement(output_xml, "Traffic")  # add new Traffic child under the root

            # get traffic ID and make sure it is unique
            traffic_id = -1
            while 1:
                traffic_id = gen_utils.get_int_descision("What is the ID for Traffic Definition "+str(traffic)+"?", 0)  # +ve

                if traffic_id in traffics_ids:  # if id not unique
                    print("ERROR: Traffic ID:", str(traffic_id), "must be unique. Current IDs:", traffics_ids, "\n")
                else:
                    traffics_ids.append(int(traffic_id))
                    break

            # if we are naming them set that here
            if node_name_mode:
                traffic_name = str(gen_utils.get_str_descision("Input name for Traffic Definition " + \
                                                               str(traffic_id)+":", alnum_only=True))
            else:
                traffic_name = "unnamed"  # else default to unnamed

            # if we are allowed to change the offsets set that here too
            if offset_set_mode:
                traffic_offset = str(gen_utils.get_float_descision("Input offset for Traffic Definition " + \
                                                                   str(traffic_id)+":", 0))
            else:
                traffic_offset = "0"  # else default to 0

            # if we are allowed to set a destination set that here too
            if dest_set_mode:
                dest = str(gen_utils.get_int_descision("Input destination for Traffic " + \
                                                       str(traffic_id)+" (0 for random):", 0))
            else:
                # 0 can never be an end station as it is always the controller so this signifies random
                dest = "0"  # default to 0

            # if we are allowed to set a size for the packets set that here too
            if size_set_mode:
                size = str(gen_utils.get_int_descision("Input packet size for Traffic " + \
                                                       str(traffic_id)+" (0 for random between 1 and 64):", 0))
                if size == 0:
                    size = random.randInt(1, 64)
                    print("Traffic", str(traffic_id), "packet size randomly set to", str(size))
            else:
                size = "16"  # default to 16 bytes


            # set this Traffic Definition base attributes
            t_ele.set("unique_id", str(traffic_id))
            t_ele.set("name", str(traffic_name))
            t_ele.set("offset", str(traffic_offset))
            t_ele.set("destination_id", str(dest))
            t_ele.set("size", str(size))


            ## determine what type of traffic this queue is for
            # get type
            traffic_type = gen_utils.get_restricted_descision("What is the Queue Type for this Traffic Definition (ID: " \
                                                              + str(traffic_id)+")?", queue_types)

            # create type node
            q_ele = etree.SubElement(t_ele, str(traffic_type))  # add traffic type element child under the traffic element

            # get type attributes and add them to the node
            if(traffic_type == queue_types[0]):  # ST

                # get required attributes of ST queues
                st_hard_deadline = gen_utils.get_float_descision("What is the \"Hard_Deadline\" for this Traffic Definition (ID: " \
                                                                 + str(traffic_id)+")?", 0)
                st_max_release_jitter = gen_utils.get_float_descision("What is the \"Max_Release_Jitter\" for this Traffic Definition (ID: " \
                                                                      + str(traffic_id)+")?", 0)
                st_period = gen_utils.get_float_descision("What is the \"Period\" for this Traffic Definition (ID: " \
                                                          + str(traffic_id)+")?", 0)

                # set attributes of element in XML
                q_ele.set("hard_deadline", str(st_hard_deadline))
                q_ele.set("max_release_jitter", str(st_max_release_jitter))
                q_ele.set("period", str(st_period))


            elif(traffic_type == queue_types[1]):  # Sporadic_Hard

                # get required attributes of ST queues
                sh_hard_deadline = gen_utils.get_float_descision("What is the \"Hard_Deadline\" for this Traffic Definition (ID: " \
                                                                 + str(traffic_id)+")?", 0)
                sh_max_release_jitter = gen_utils.get_float_descision("What is the \"Max_Release_Jitter\" for this Traffic Definition (ID: " \
                                                                      + str(traffic_id)+")?", 0)
                sh_min_inter_release = gen_utils.get_float_descision("What is the \"Min_Inter_Release\" for this Traffic Definition (ID: " \
                                                                     + str(traffic_id)+")?", 0)

                # set attributes of element in XML
                q_ele.set("hard_deadline", str(sh_hard_deadline))
                q_ele.set("max_release_jitter", str(sh_max_release_jitter))
                q_ele.set("min_inter_release", str(sh_min_inter_release))


            elif(traffic_type == queue_types[2]):  # Sporadic_Soft

                # get required attributes of ST queues
                ss_soft_deadline = gen_utils.get_float_descision("What is the \"Soft_Deadline\" for this Traffic Definition (ID: " \
                                                                 + str(traffic_id)+")?", 0)
                ss_max_release_jitter = gen_utils.get_float_descision("What is the \"Max_Release_Jitter\" for this Traffic Definition (ID: " \
                                                                      + str(traffic_id)+")?", 0)
                ss_min_inter_release = gen_utils.get_float_descision("What is the \"Min_Inter_Release\" for this Traffic Definition (ID: " \
                                                                     + str(traffic_id)+")?", 0)

                # set attributes of element in XML
                q_ele.set("soft_deadline", str(ss_soft_deadline))
                q_ele.set("max_release_jitter", str(ss_max_release_jitter))
                q_ele.set("min_inter_release", str(ss_min_inter_release))

            elif(traffic_type == queue_types[3]):  # BE
                # best effort queues have no timing constraints
                pass


            else:  # error unrecognised type
                print("ERROR: Did not recognise Traffic Definition Queue type:", str(traffic_type))



        # everything for every traffic type defined, output
        self.output(filename, output_xml)



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

# fn = "simulator_files\\M_traffic_definition.xml"
# generate(fn)
