"""
Command line interface to generate the queue definition xml by stating everything manually over cli

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
def generate(filename, max_nodes=0, id_list=-1, allowed_schedules=-1):

    # if max_nodes not set (or incorrectly set) by function, ask the user for an amount
    if max_nodes < 2:
        # must be more than 3 nodes due to there needing to be at least 1 of (controller & switch & end_station)
        max_nodes = gen_utils.get_int_descision("What is the maximum number of nodes?", 3, 100)


    # check if the user has gave an id_list
    if id_list == -1:  # not provided
        id_list = []
    else:
        print("Using provided ID list:", id_list)  # should this be printed? Does the user care?


    # check if the user has provided an allowed_schedules list
    if allowed_schedules == -1:  # not provided
        allowed_schedules = ["FIFO"]  # default to FIFO only
    else:
        print("Using provided allowed schedules list:", allowed_schedules)  # should this be printed? Does the user care?


    # begin generation
    Generator(filename, max_nodes, id_list, allowed_schedules)




##################################################
################ GENERATOR OBJECT ################
##################################################

class Generator():

    def __init__(self, filename, max_nodes, id_list, allowed_schedules):

        # setup the XML tree
        output_xml = etree.Element("Queue_Definition_Root")  # default root node


        # get amount of switches
        if len(id_list) == 0:
            provided_id_list = False
            switches_count = gen_utils.get_int_descision("How many switches (including the Controler) are in the network?", 2, int((max_nodes/2)-1))
        else:
            provided_id_list = True
            switches_count = len(id_list)
        print("Continuing with", switches_count, "switches")


        # loop over all switches
        for switch in range(switches_count):

            queues_count = 0
            queues_reserved = 5  # must have 1 of each queue

            ## get switch ID
            switch_id = -1
            if (not provided_id_list) and (switch == 0):  # if there was no provided ID list then we make sure there is a controller (at ID 0)
                print("Using Switch ID: 0 for first switch")
                switch_id = 0
            elif not provided_id_list:  # otherwise ask the user for an ID to use for this switch
                switch_id = gen_utils.get_int_descision("What is the ID for Switch "+str(switch)+"?", 0)  # +ve
            else:  # else the ID list is provided
                switch_id = int(id_list[switch])


            ## get queue counts
            # ST
            st_count = str(gen_utils.get_int_descision("How many ST Queues are there in Switch ID: "+str(switch_id)+"?", \
                                                       1, (8-queues_count-queues_reserved)))
            queues_count += int(st_count)
            queues_reserved -= 1

            # Emergency
            e_count = str(gen_utils.get_int_descision("How many Emergency Queues are there in Switch ID: "+str(switch_id)+"?", \
                                                      1, (8-queues_count-queues_reserved)))
            queues_count += int(e_count)
            queues_reserved -= 1

            # Sporadic Hard
            sh_count = str(gen_utils.get_int_descision("How many Sporadic_Hard Queues are there in Switch ID: "+str(switch_id)+"?", \
                                                       1, (8-queues_count-queues_reserved)))
            queues_count += int(sh_count)
            queues_reserved -= 1

            # Sporadic Soft
            ss_count = str(gen_utils.get_int_descision("How many Sporadic_Soft Queues are there in Switch ID: "+str(switch_id)+"?", \
                                                       1, (8-queues_count-queues_reserved)))
            queues_count += int(ss_count)
            queues_reserved = 0

            # Best Effort
            be_count = str(gen_utils.get_int_descision("How many BE Queues are there in Switch ID: "+str(switch_id)+"?", \
                                                       1, (8-queues_count)))
            queues_count += int(be_count)


            # see if the user wants to use a scheduling policy other than default
            if gen_utils.get_YesNo_descision("Would you like to alter the scheduling policy of any of these Queues for Switch ID: "+str(switch_id)+"?"):
                st_sched = gen_utils.get_restricted_descision("What is the scheduling policy for the ST Queue?", allowed_schedules)
                e_sched = gen_utils.get_restricted_descision("What is the scheduling policy for the Emergency Queue?", allowed_schedules)
                sh_sched = gen_utils.get_restricted_descision("What is the scheduling policy for the Sporadic_Hard Queue?", allowed_schedules)
                ss_sched = gen_utils.get_restricted_descision("What is the scheduling policy for the Sporadic_Soft Queue?", allowed_schedules)
                be_sched = gen_utils.get_restricted_descision("What is the scheduling policy for the BE Queue?", allowed_schedules)
            # else they default to FIFO
            else:
                print("Defaulting all Queue schedules to \"FIFO\"")
                st_sched = "FIFO"
                e_sched = "FIFO"
                sh_sched = "FIFO"
                ss_sched = "FIFO"
                be_sched = "FIFO"


            ## build node for this switch and add to the XML file
            # build main part
            r_switch = etree.SubElement(output_xml, "Switch")  # add Switch child under the root
            r_switch.set("unique_id", str(switch_id))  # add its id
            switch_queues = etree.SubElement(r_switch, "Queues")  # prepare queue element

            # ST
            q_st = etree.SubElement(switch_queues, "ST")
            q_st.set("count", st_count)
            q_st.set("schedule", st_sched)

            # Emergency
            q_emergency = etree.SubElement(switch_queues, "Emergency")
            q_emergency.set("count", e_count)
            q_emergency.set("schedule", e_sched)

            # Sporadic_Hard
            q_sh = etree.SubElement(switch_queues, "Sporadic_Hard")
            q_sh.set("count", sh_count)
            q_sh.set("schedule", sh_sched)

            # Sporadic_Soft
            q_ss = etree.SubElement(switch_queues, "Sporadic_Soft")
            q_ss.set("count", ss_count)
            q_ss.set("schedule", ss_sched)

            # Best_Effort
            q_be = etree.SubElement(switch_queues, "BE")
            q_be.set("count", be_count)
            q_be.set("schedule", be_sched)


        # everything for every switch defined, output
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

# fn = "simulator_files\\M_queue_definition.xml"
# idlist = [0, 10, 100, 1000]
# allowed_words = ["FIFO", "HTML"]
# generate(fn, max_nodes=100, id_list=idlist, allowed_schedules=allowed_words)
