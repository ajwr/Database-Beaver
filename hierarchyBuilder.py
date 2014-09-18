from owlwriter import ontology
from collections import defaultdict
import MySQLdb
import sys

"""Supplementory file  containing functions to build the Hierarchy \
    and clean up the relationships

This software is Copyright (c) 2014 The Regents of the University of California. All Rights Reserved.

Permission to copy, modify, and distribute this software and its documentation for educational, research and non-profit purposes, without fee, and without a written agreement is hereby granted, provided that the above copyright notice, this paragraph and the following three paragraphs appear in all copies.

Permission to make commercial use of this software may be obtained by contacting:

    Technology Transfer Office
    9500 Gilman Drive, Mail Code 0910
    University of California
    La Jolla, CA 92093-0910
    (858) 534-5815
    invent@ucsd.edu

    This software program and documentation are copyrighted by The Regents of the University of California. The software program and documentation are supplied "as is", without any accompanying services from The Regents. The Regents does not warrant that the operation of the program will be uninterrupted or error-free. The end-user understands that the program was developed for research purposes and is advised not to rely exclusively on the program for any reason.

    IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE TO
    ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR
    CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING
    OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION,
    EVEN IF THE UNIVERSITY OF CALIFORNIA HAS BEEN ADVISED OF
    THE POSSIBILITY OF SUCH DAMAGE. THE UNIVERSITY OF
    CALIFORNIA SPECIFICALLY DISCLAIMS ANY WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
    THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS, AND THE UNIVERSITY OF CALIFORNIA HAS NO OBLIGATIONS TO
    PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
    MODIFICATIONS.
"""


# Cleans up the passed in translated dictionary by removing unneccessary
# Nodes in the hierarchy
def cleanUpRelations(progressList, leaves, pValid, cleanRelations, translatedDict, \
                     parent, childList, loopsDict = defaultdict(list)):
    """Cleans up the passed in translated dictionary by removing nodes
    violating the Two or More Children Policy. Returns the new hierarchy
    through output dictionary parameter cleanRelations.

    Input:
        progressList: List object that keeps track of the nodes already
                      traversed. Used for loop detection.
        leaves: List object containing the translated input CUIs
        pValid: Holds the cui-name of the last valid parent
        cleanRelations: Dictionary object holding the new cleaned-up dictionary
        translatedDict: Dictionary object containing the relationships and nodes
                        to be cleaned up
        parent: Holds the cui-name of the current parent being traversed
        childList: List object that holds the list of children for the current
                   parent
        loopsDict: Dictionary object that saves the loops found during clean-up
    """

    # Save valid parent
    valid = pValid

    # Check if Current Parent is valid (2 or more children)
    if len(childList) > 1:
        isValid = True
    else:
        isValid = False

    # Exclusive Case: When the parent is not valid but it is an input CUI
    # it is considered valid regardless of its child count
    if parent in leaves:
        isValid = True

    # Check if Current node is a leaf node, if so connect it to the last
    # valid parent
    if parent in leaves and parent not in cleanRelations[pValid] and \
            parent != pValid:
        cleanRelations[pValid].append(parent)

    # If current parent is valid, add it to the cleaned dictionary if not
    # already present.
    if isValid and parent not in cleanRelations[pValid] and parent != pValid:
        cleanRelations[pValid].append(parent)

        # Set pValid to new valid parent (current)
        valid = parent

    # Update valid parent
    if isValid:
        valid = parent

    # Loop through children and recursively call
    for child in childList:
        # Skip any 'holder' children
        if child == 'holder':
            continue

        # Check if child has already been traversed
        if child in progressList:
            loopCount = len(loopsDict["loops"])
            badChild = "{}-BAD".format(child)
            badChild += str(loopCount)

            # Continue if already found the loop
            if isContainedIn(loopsDict, badChild, "loops"):
                continue


            # Determine beginning and end of the loop
            loopIterator = progressList.index(child) + 1
            loopEnd = len(progressList)


            # Root the child as the start of the loop
            loopsDict["loops"].append(badChild)

            # Save the remaining loop
            while loopIterator < loopEnd:
                loopsDict[badChild].append("{}-BAD{}".format( \
                        progressList[loopIterator], loopCount))


                # Increment iterator and reassign badChild
                badChild = "{}-BAD{}".format(progressList[loopIterator], \
                                             loopCount)
                loopIterator += 1

            # Continue to next child
            continue

        # Add current child to progresslist
        pathSoFar = list(progressList)
        pathSoFar.append(child)

        #Recursive call
        cleanUpRelations(pathSoFar, leaves, valid, cleanRelations, translatedDict, \
                         child, translatedDict[child], loopsDict)


# Eliminates redundant relationships in the hierarchy
def reduceRedundancy(ancestorList, relationsDict, parent, childList, \
                    translatedLeaves):
    """Elimanates redundant relationships in the hierarchy. A relationship is
    considered redudnant when it directly connects two nodes which already
    have an indirect relationship. Directly alters the passed in relationsDict

    Input:
        ancestorList: List that contains the list of ancestors already
                      traversed. Used for checking for redundancy
        relationsDict: Dictionary containing the relationships to be
                       cleaned-up. Directly alters this dictionary object for
                                   implicit return.
        parent: String containing the cui-name of the current parent being
                traversed.
        childList: List containing the cui-names of the children of the current
                   parent.
        translatedLeaves: List containing the input CUIs (in cui-name form)

    """
    relationsRemoved = 0

    # Check for redundant relationships
    for child in childList:
        # Skip holder
        if child == 'holder':
            continue

        # Remove redundant relationship between the child and any ancestors
        for ancestor in ancestorList:
            # Skip iteration if ancestor is no longer in the dict
            if ancestor not in relationsDict:
                continue
            # check if child has a direct relationship to an ancestor
            if child in relationsDict[ancestor]:
                try:
                    # Remove relationship between child and ancestor
                    cToFix = relationsDict.pop(ancestor)

                    relationsRemoved += 1
                except KeyError:
                    print ("KeyError when accessing {}".format(ancestor))
                    return

                # Add the fixed ancestor
                for entry in cToFix:
                    # Append the entry to the new ancestor if not the child
                    if entry != child:
                        relationsDict[ancestor].append(entry)



    # Create a copy of ancestor list to recursively pass on
    newAncestors = list(ancestorList)
    newAncestors.append(parent) # Add current parent to ancestor list

    # Recursively traverse children
    for child in childList:
        # Skip holder
        if (child == 'holder'):
            continue
        relationsRemoved += reduceRedundancy (newAncestors, relationsDict, child, \
                        relationsDict[child], translatedLeaves)

    return relationsRemoved


# Writes the hierarchy in XML format for protege
def writeToFile (translatedLeaves, relationsDict, filename, topHier, loopDict):
    """Writes the hierarchy in OWL format to the specified file for use with
    Protege.

    Input:
        translatedLeaves: List containing the input CUIs (in cui-name format)
        relationsDict: Dictionary containing the relationships describing the
                       final hierarchy to be written to the file
        filename: String naming the file to be used for saving the final
                  hierarchy.
        topHier: List containing the top level CUIs (in cui-name format)
        loopDict: Dictionary containing the loops found

    """
    # Create an ontology object
    hierarchy = ontology(filename)

    # Write XML version
    hierarchy.version("1.0")

    # Write doctype header
    hierarchy.doctype()

    # Write rdfHeader
    hierarchy.rdfHeader(
        "http://www.semanticweb.org/alexrichardson/ontologies/2014/6/UMLS_subset")

    # Write header for start of classes
    hierarchy.classes()

    childDict = defaultdict(list)

    # Reorganize the relations dictionary to be child-based
    for nameCui in topHier:
        # Clean illegal symbols (not valid in OWL format) from the names-cuis
        cleanNameCui = nameCui
        # Add top level node to dictionary
        childDict[cleanNameCui].append('none')
        reorganize(childDict, relationsDict, nameCui)

    # Clean up loops category
    reorganize (childDict, loopDict, "loops")

    # Clean up the misc category
    for cui in translatedLeaves:
        if not childDict.has_key(cui):
            childDict[cui].append('misc')


    # Add classes to the hierarchy
    for child, parentList in childDict.items():
        # Skip holder children
        if child == 'holder':
            continue

        # Clean up child's name by removing illegal symbols in protege
        child = child
        hierarchy.addClass (child, parentList)

    # Write the ending statement
    hierarchy.end()


# Reorganizes the relations dictionary and returns a child-based one
def reorganize (newDict, oldRelationsDict, parent):
    """Reorganizes the parent-based relations dictionary and returns a
    child-based dictionary through output reference parameter newDict

    Input:
        newDict: Dictionary to save the reorganized parent-based relations
                 dictionary in. Output parameter used to return the child-based
                 dictionary.
        oldRelationsDict: Parent-based relations dictionary to be reorganized.
        parent: String containing the current parent's name.
    """

    # Add current parent to each of its children's entries
    for child in oldRelationsDict[parent]:
        if parent not in newDict[child] and child != 'holder':
            newDict[child].append(parent)

    # Recursive call to traverse hierarchy
    for child in oldRelationsDict[parent]:
        reorganize (newDict, oldRelationsDict, child)


# Traverses a pathway to check for the presence of a node
def isContainedIn (loopsDict, toFind, parent):
    """Traverses a pathway to check for the presence of a node. Returns True
    if found, false otherwise.

    IOnput:
        loopsDict: Dictionary to check against for the presence of the node
                   toFind.
        toFind: String naming the cui-name of the node to check for in the
                loopsDict.
        parent: String naming the cui-name of the current parent node being
                traversed while checking for the toFind node.
    """

    # Check if found the node
    for node in loopsDict[parent]:
        if matches (toFind, node):
            return True

    # Check if the node toFind is contained in any of the children's hierarchies
    for child in loopsDict[parent]:
        if (isContainedIn (loopsDict, toFind, child)):
            return True

    return False


# Determines if two cuiName combinations contain the same CUI
def matches (name1, name2):
    """Determine if two cui-name combinations describe the same concept (have
    matching cuis). Returns True if the cuis match, false otherwise.

    Input:
        name1: String representing the cui-name to check against name2.
        name2: String representing the cui-name to check against name1.
    """

    iterator = 0 # Tracks the number of cui characters checked
    # Check for a match between the CUIs
    while iterator != 8:
        # Check for matching letter
        if name1[iterator] == name2[iterator]:
            iterator += 1
            continue
        else: # Return false if no match
            return False

    # Return true if end of CUI is successfully reached
    return True


# Returns the preferred term for a CUI
def determinePreferred (ttyStrLatQuery):
    """Return the string containing the preferred term for a CUI after removing
    any illegal characters that would cause Protege reading errors.

    Input:
        names: List of tuples containing pairs of (TTY, String Name) of a cui.
        A tty of 'PT' indicated the Prefered Term.
    """

    # Default return if no english or preferred term
    englishTerm = "No English term"     # Loop through names until found the preferred term

    for tty, string, language in ttyStrLatQuery:
        # Return the preferred term
        if tty == 'PT':
            return removeIllegalChars(string)
        if language == 'ENG' and englishTerm == 'No English term':
            englishTerm = string

    # If not preferred term, use the first English term available
    return removeIllegalChars(englishTerm)

def areValidArguments(arguments):
    """Returns true if the commandline arguments passed are valid.

    The arguments are considered valid if either all three parameter files
    are provided (inputFile, topHier, and outputFile), or if none are. The
    -x for debug mode and logfile are optional in both cases.

    Input:
        arguments: The commandline arguments passed in to the main script"""

    # Calling the UMLSSubsetBuilder with no commandline arguments is valid
    if len(arguments) == 1:
        return True
    # If only 1 or 2 arguments are provided, they must be for debug mode
    if len(arguments) == 2 or len(arguments) == 3:
        if arguments[1] == '-x':
            return True
        else:
            return False
    # If 3 arguments are provided, they could be all be for debug or all
    # describe files for input. Both are assumed to be true.
    if len(arguments) == 4:
            return True
    # If 4, 5, or 6 arguments are provided, the 4th must be for debug mode
    if len(arguments) == 5 or len(arguments) == 6 or len(arguments) == 7:
        if arguments[4] == '-x':
            return True
        else:
            return False

def removeIllegalChars (cuiName):
    """Removes any illegal characters that would cause Protege read errors
    from the cui-name. Returns the fixed cui-name.

    Input:
        cui-name: The string containing the cui-name to clean up."""

    cuiName = cuiName.replace(' ', '_').replace('(', '').replace(')', '').\
            replace(',', '').replace("\'", '').replace("\"", '').\
            replace("[","").replace("]", "").replace("&", "and").\
            replace("<","").replace(">","").replace("%","percent").\
            replace("--","-").replace("^","").replace(';','-').\
            replace('/','or')

    return cuiName

def translateDictionary (untranslatedDict, dbCursor):
    """Translates a dictionary passed in by adding the Preferred Term or
    English term to the end of the CUI. Returns the translated dictionary

    Input:
        untranslatedDict - the dictionary to be translated
        dbCursor - the database cursor used for querying"""

    translatedDict = defaultdict(list)

    # Translate the untranslatedDict from concepts to descriptions
    stringQuery = "SELECT TTY, STR, LAT from MRCONSO where CUI = '{}' "
    for parent, childList in untranslatedDict.items():
        # Add the parent concept to the dictionary with string name
        try:
            dbCursor.execute(stringQuery.format(parent))

        except MySQLdb.Error, e:
            try:
                # Prints the error
                print "MySQL Error [{}]: {} --- while querying {}".format(\
                                                    e.args[0], e.args[1], parent)

            except IndexError:
                # Prints the 1 argument error
                print "MySQL Error: {} --- while querying {}".format(str(e), parent)

            sys.exit()



        # Fetch parent's name
        pRows = dbCursor.fetchall()


        # Handle misc case
        if parent == 'misc':
            pName = 'misc'
        else:
            # Save Parent's Name
            pName = "{}".format(determinePreferred (pRows))
            pName = "{}-".format(parent) + pName

        # Fetch Children names and add to the translated dict
        for child in childList:
            try:
                dbCursor.execute(stringQuery.format(child))

            except MySQLdb.Error, e:
                try:
                    # Prints the error
                    print "MySQL Error [{}]: {} --- while querying {}".format(\
                                        e.args[0], e.args[1], child)

                except IndexError:
                    # Prints the 1 argument error
                    print "MySQL Error: {} --- while querying {}".format(str(e),\
                                                                        child)

            # Fetch child's names
            cRows = dbCursor.fetchall()

            # Save the name
            if child == 'holder':
                cName = 'holder'
            else:
                cName = "{}".format(determinePreferred(cRows))
                cName = "{}-".format(child) + cName

            # Add child too dictionary
            translatedDict[pName].append(cName)

    return translatedDict

def translateList (untranslatedList, dbCursor):
    """Translates an inputted list by adding the Preferred Term or English
    term to the end of the CUI. Returns the translated list.

    Input:
        untranslatedList: the list to be translated
        dbCursor: the database cursor for querying"""

    translatedLeaves = []

    # Translate the leaves from concepts to descriptions
    stringQuery = "SELECT TTY, STR, LAT from MRCONSO where CUI = '{}' "
    for cui in untranslatedList:
        # Add the parent concept to the dictionary with string name
        try:
            dbCursor.execute(stringQuery.format(cui))

        except MySQLdb.Error, e:
            try:
                # Prints the error
                print "MySQL Error [{}]: {} --- while querying {}".format(\
                                                    e.args[0], e.args[1], cui)

            except IndexError:
                # Prints the 1 argument error
                print "MySQL Error: {} --- while querying {}".format(str(e), cui)



        # Fetch leaf's name
        lRows = dbCursor.fetchall()

        # Save Parent's Name
        lName = "{}".format(determinePreferred(lRows))
        lName = "{}-".format(cui) + lName

        # Add child too dictionary
        translatedLeaves.append(lName)


    return translatedLeaves
