"""
Contains functions that are re-used accros all generators. Mainly used to gather user inputs
"""
##################################################
##################### IMPORT #####################
##################################################

import string


##################################################
################ HELPER FUNCTIONS ################
##################################################

# Helper function to ask the user a question and get a YES (True) or NO (False) answer
def get_YesNo_descision(prompt_question):
    final_descision = "loop"

    # ask the user the text given in function until a "Y" or "N" es entered
    while final_descision == "loop":
        descision = input(prompt_question + " (Y/N): ")

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

    # critical error if max int smaller than min int
    if max_int < min_int:
        print("CRITICAL ERROR: max_int cant be smaller than min_int in function get_int_descision", \
              "MAX:", max_int, "MIN:", min_int)
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

    return int(final_count)



# Helper function to return an alphanumeric string (not allowed special characters) optional testing for only alpha strings
def get_str_descision(prompt_question, alpha_only=False, alnum_only=False, restricted_only=False):
    final_answer = "@false@"

    # Determine mode
    if alpha_only:
        while not final_answer.isalpha():
            final_answer = input(prompt_question+": ")

            if final_answer.isalpha():
                break
            else:
                print("\""+final_answer+"\"", "is not an alphabetic string (no spaces or numbers allowed)")

    # if alphanumeric
    elif alnum_only:
        while not final_answer.isalnum():
            final_answer = input(prompt_question+": ")

            if final_answer.isalnum():
                break
            else:
                print("\""+final_answer+"\"", "is not an alphanumeric string (no spaces or special characters allowed)")

    # if windows friendly symbols
    elif restricted_only:
        while 1:
            valid_chars = "_. %s%s" % (string.ascii_letters, string.digits)

            final_answer = input(prompt_question+": ")

            for c in final_answer:
                if c not in valid_chars:
                    print("\""+final_answer+"\"", "contains illegal char \""+c+"\"", \
                          "Must be an alphanumeric string containing only _ or . special chars and no spaces")
            break

    # anything
    else:
        final_answer = input(prompt_question+": ")

    return str(final_answer)



# Helper function to ask the user a question and get response from an allowed list of strings
def get_restricted_descision(prompt_question, allowed_strings_list):
    final_descision = "loop@F"

    # ask the user the text given in function until a "Y" or "N" es entered
    while final_descision == "loop@F":
        descision = input(prompt_question + " ")

        if descision in allowed_strings_list:
            return descision

        else:
            print("\""+descision+"\"", "unrecognised. Must be one of either:", allowed_strings_list)
