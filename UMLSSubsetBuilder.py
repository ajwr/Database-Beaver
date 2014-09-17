#!/usr/bin/python
import MySQLdb
import sys
import os
from datetime import datetime
from collections import defaultdict
from hierarchyBuilder import cleanUpRelations, writeToFile, reduceRedundancy, \
    determinePreferred, areValidArguments

"""This program develops a hierarchy from a set of input CUIs. Outputs the
hierarchy in OWL format for use with Protege.

    The hierarchy is characterized by a "Two or More Child" Policy per node
as well as a "No Redundancy" Policy for relationships.

Usage: UMLSSubsetBuilder.py [inputFile][topTier][finalHierarchyFile][-x DebugMode]
                            [logfile][dirtyHierarchyFile]


Note: If no commandline arguments are given, then the default files specified in
the configuration file will be used. Either all 3 files must be provided or none
at all.

Input:
    inputFile  = The file containing the CUIs to include and create the
                 hierarchy off of.
    topTier    = The file containing the top-level CUIs to build the hierarchy
                 up to.
    finalHierarchyFile = The file to output the FinalHierarchy to.
    -x         = [Optional] Will enable debug mode which will log various
                 datastructures created as well as the number of
                 relationships removed in each run through the redundancy
                 reduction algorithm. It will also save the initial hierarchy
                 created to the file specified in the configuration file. See
                 the README file for more information on debug mode.
    logfile    = [Optional] If provided, The file to log to when debug mode
                 is enabled.
    dirtyHierarchyFile = [Optional] When debug mode is enabled, if provided,
                         the file will be used to save the initial hierarchy
                         before it undergoes the clean-up process.

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

# Maximum times to continue clean-up when # of relations removed is the same
MAXREDUNDANT = 50
FILENAME = 'UMLSSubsetBuilder.py' # Current file's name
LINENUMBER = 10 # Line number of MAXREDUNDANT variables
CONFIGURATIONFILE = 'config.txt'
debugOn = False # Debug mode default is off

startTime = datetime.now()
lastTime = startTime # Time script was started, used to track progress
TIMETRACKING = True
timeElapsed = 0

# Unbuffered stdout
unbuffered = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stdout = unbuffered

# Configuration Attributes
configAttributes = ['username','password','port','databasename','hostname',\
               'inputCUIFile','topLevelTierFile','finalHierarchyFile','logFile',\
               'dirtyHierarchyFile']
configs = dict()

# Print usage message
if len(sys.argv) > 1 and sys.argv[1] == '-u':
    print "Usage: UMLSSubsetBuilder.py [inputFile][topTier][finalHierarchyFile][-x DebugMode][logfile][dirtyHierarchyFile]"
    print "See README or .___doc__ for more informations."
    sys.exit()

# Print usage message if incorrect # of command line args
if not areValidArguments(sys.argv):
    print "Incorrect # of arguments"
    print """Usage: UMLSSubsetBuilder.py [inputFile][topTier][finalHierarchyFile][-x DebugMode][logfile][dirtyHierarchyFile]
    Note: either all 3 parameter files must be provided or none at all.
    For example:
        UMLSSubsetBuilder.py inputFile topTier finalHierarchyFile [-x DebugMode][logfile][dirtyHierarchyFile]
        or
        UMLSSubsetBuilder.py [-x DebugMode][logfile][dirtyHierarchyFile]"""

    sys.exit()


# Open configuration file for accessing the UMLS database
try:
    configFile = open(CONFIGURATIONFILE,'r')
except IOError:
    print "IOError when trying to open configuration file ({}).".format(\
                                                        CONFIGURATIONFILE)
    sys.exit()
except NameError:
    print "NameError when trying to open configuration file ({}).".format(\
                                                        CONFIGURATIONFILE)
    sys.exit()


# Set the configuration variables for accesing the UMLS
for configLine in configFile:
    # Continue when found a comment beginning with '#'
    if configLine.startswith('#'):
        continue

    # Find delimiter
    delimIndex = configLine.find('=')

    # Continue if no configuration attribute is given on this line, -1
    # indicates that '=' was not found in the line
    if delimIndex == -1:
        continue

    # Add the configuration attribute to the config dictionary
    configs[configLine[:delimIndex].lstrip(' ')] = configLine[delimIndex+1:].\
        rstrip('\n')

# check for the presence of all configuration attributes
for attribute in configAttributes:
    # Print error message if an attribute is not present
    if attribute not in configs:
        print "Error: {} not provided in configuration file.".format(attribute)

        #Print error message for config file format
        print """Configuration file is improperly formatted.
        Please refer to the README.install file for formatting guidelines."""

        sys.exit()


# Set Debug mode
if (len(sys.argv) >= 5 and sys.argv[4] == '-x') or (len(sys.argv) >= 2\
        and sys.argv[1] == '-x'):
    debugOn = True

# Save desired logFile  and dirtyHierarachyFile if specified by commandline
# arguments
if debugOn:
    # Save logfile
    if len(sys.argv) == 3 or len(sys.argv) == 4:
        configs['logFile'] = sys.argv[2]
    elif len(sys.argv) == 6 or len(sys.argv) == 7:
        configs['logFile'] = sys.argv[5]

    # Save the dirtyHierarchyFile if it is provided
    if len(sys.argv) == 4:
        configs['dirtyHierarchyFile'] = sys.argv[3]
    elif len(sys.argv) == 7:
        configs['dirtyHierarchyFile'] = sys.argv[6]

# Open the file to be used for logging
if debugOn:
    logFile = open(configs['logFile'], 'a')

# Format LogFile
if debugOn:
    logFile.write("\n\nLog for : {}---------------------------------------------------" \
                "-----------------------------------------\n".format( \
                    datetime.today()))

# Save commandline argument files to use if provided
if (len(sys.argv) == 4 and not debugOn) or (len(sys.argv) > 4):
    configs['inputCUIFile'] = sys.argv[1]
    configs['topLevelTierFile'] = sys.argv[2]
    configs['finalHierarchyFile'] = sys.argv[3]


# Open input files
try:
    inFile = open(configs['inputCUIFile'], 'r')
except IOError, NameError:
    print "An Error occurred while trying to open {}".format(\
                                            configs['inputCUIFile'])
    sys.exit()
try:
    topTierFile = open(configs['topLevelTierFile'], 'r')
except IOError, NameError:
    print "An Error occurred while trying to open {}".format(\
                                            configs['topLevelTierFile'])
    sys.exit()




# Create hierarchy sets from files
topTier = set(line.rstrip('\n').rstrip().lstrip() for line in topTierFile)

# Read file input CUIs into the Parent list stripped of \n
parentList = [line.rstrip('\n').rstrip().lstrip() for line in inFile] # List of parent CUIs
leaves = list(parentList) # Keeps track of original input CUIs


# Tracks the parent CUIs processed (considered to be children post-processing)
# Prevents redundant traversals and processing CUIs already handled
childrenSet = set()

# Initialize Relationship defaultDictionary which will hold all the
# inititially gathered relationships for the input CUIs. Will contain
# much excess information irrelevant to the final hierarchy
relationsDict = defaultdict(list)

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to intilaize all dictionaries, sets, and lists".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime

# Establish a connection and cursor to MySQL UMLS database
# Connect to MySQL server
try:
    cnx = MySQLdb.connect (host=configs['hostname'], user=configs['username'],\
                           port=int(configs['port']), passwd=configs['password'],\
                           db=configs['databasename'])

# Catch errors from MySQL
except MySQLdb.Error, e:
    try:
        # Prints the error
        print "MySQL Error [{}]: {}".format(e.args[0], e.args[1])

    except IndexError:
        # Prints the 1 argument error
        print "MySQL Error: {}".format(str(e))

    sys.exit()


# Establish cursor for queries
cur = cnx.cursor()

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to establish connection to MySQL and establish cursor".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime

# Establish string for queries
query = "SELECT CUI1, REL, CUI2, SAB from MRREL where CUI2 = '{}'" \
        "AND SAB = 'MTH' AND (REL = 'RN' OR REL = 'CHD')"


# Check the initial parent queue for top level concepts
for i in range(len(parentList)):
    # Pop the first parent off
    temp = parentList.pop(0)

    # Add the parent to the relationsDict with child being "holder" if parent
    # is a top level concept
    if temp in topTier:
        relationsDict[temp].append("holder")

    # Else add the parent back into the parentList
    else:
        parentList.append(temp)

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to check the initial parent queue for top lvl concepts".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime


# Relationship Harvesting: Loops through the Parent Queue making queries until
# all relationships relevant to the input CUIs are gathered
while True:
    # Break when parent queue is empty
    if not parentList:
        break

    # Establish connection and query MySQL database
    try:
        # Obtain CUI of poppedParent to query parents
        pParent = parentList.pop(0)

        # Executue a query serach
        cur.execute (query.format(pParent))

    # Catch errors from MySQL
    except MySQLdb.Error, e:
        try:
            # Prints the error
            print "MySQL Error [{}]: {} --- while querying {}".format(\
                                                e.args[0], e.args[1], pParent)

        except IndexError:
            # Prints the 1 argument error
            print "MySQL Error: {} --- while querying {}".format(str(e),\
                                                                pParent)

        sys.exit()

    # Add popped Parent (now a child) to the Child set
    childrenSet.add(pParent)

    # Save Results
    rows = cur.fetchall()

    # Add current node to misc category if it has no parents
    if not rows:
        if (pParent not in relationsDict["misc"]):
            relationsDict["misc"].append(pParent)
        continue

    # Process the resulting query
    for result in rows:
        # Assign information from query
        cui1 = result[0]
        rel = result[1]
        cui2 = result[2]
        sab = result[3]


        # Add the relationship to the Relationship Dictionary
        if (cui2 not in relationsDict[cui1]):
            relationsDict[cui1].append(cui2)

        # Check if the parent is a top level concept, if it is continue to the
        # next iteration
        if cui1 in topTier:
            continue

        # Check if the potential parent is already in the forest if it is not
        # then add it to the parentList
        if cui1 not in childrenSet:
            parentList.append(cui1)

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to gather all initial relationships".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime


# Contains the complete initial relationsDict translated by adding the
# preferred English name of the CUI to the end of the CUI to create a cui-name
# format; used for debug purposes
translatedDict = defaultdict(list)

# Translate the relationsDict from concepts to descriptions
stringQuery = "SELECT TTY, STR, LAT from MRCONSO where CUI = '{}' "
for parent, childList in relationsDict.items():
    # Add the parent concept to the dictionary with string name
    try:
        cur.execute(stringQuery.format(parent))

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
    pRows = cur.fetchall()


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
            cur.execute(stringQuery.format(child))

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
        cRows = cur.fetchall()

        # Save the name
        if child == 'holder':
            cName = 'holder'
        else:
            cName = "{}".format(determinePreferred(cRows))
            cName = "{}-".format(child) + cName

        # Add child too dictionary
        translatedDict[pName].append(cName)

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to translate relationsDict".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime

# Contains the 'translated 'input CUIs in a cui-name format for easier
# readability
translatedLeaves = []
# Translate the leaves from concepts to descriptions
stringQuery = "SELECT TTY, STR, LAT from MRCONSO where CUI = '{}' "
for leaf in leaves:
    # Add the parent concept to the dictionary with string name
    try:
        cur.execute(stringQuery.format(leaf))

    except MySQLdb.Error, e:
        try:
            # Prints the error
            print "MySQL Error [{}]: {} --- while querying {}".format(\
                                                e.args[0], e.args[1], leaf)

        except IndexError:
            # Prints the 1 argument error
            print "MySQL Error: {} --- while querying {}".format(str(e), leaf)



    # Fetch leaf's name
    lRows = cur.fetchall()

    # Save Parent's Name
    lName = "{}".format(determinePreferred(lRows))
    lName = "{}-".format(leaf) + lName

    # Add child too dictionary
    translatedLeaves.append(lName)

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to translate leaves from concepts to descriptions".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime

# Will hold the hierarchy while being built and cleaned up
inProgressHier = defaultdict(list)

# Keeps track of the topTier translated
translatedTopHier =[]

# Keeps tracks of loops encountered
loopsDict = defaultdict(list)


# Create the initial hierarchy, by following pathways from topTier CUIs
for cui in topTier:
    # Query the cui to obtain its name
    try:
        cur.execute("SELECT TTY, STR, LAT from MRCONSO where CUI = '{}'".format(cui))
    except MySQLdb.Error, e:
        try:
            # Prints the error
            print "MySQL Error [{}]: {} --- while querying {}".format(\
                                                    e.args[0], e.args[1], cui)

        except IndexError:
            # Prints the 1 argument error
            print "MySQL Error: {} --- while querying {}".format(str(e),cui)



    # Fetch parent's name
    pName = cur.fetchall()

    pNameCui = "{}".format(determinePreferred(pName))

    pNameCui = "{}-".format(cui) + pNameCui

    # Save the translated cui name combination
    translatedTopHier.append(pNameCui)

    # Save parent and child for traversal
    if (translatedDict.has_key(pNameCui)):
        childList = translatedDict[pNameCui]
    else:
        continue

    # Add the Top Level Concept to the dictionary
    inProgressHier[pNameCui].append("holder")
    pathSoFar = [pNameCui]
    cleanUpRelations(pathSoFar, translatedLeaves, pNameCui, inProgressHier,\
                      translatedDict, pNameCui, childList, loopsDict)

# Save the initial hierarchy created pre-cleanup if debug is on
if debugOn:
    initialHierarchy = inProgressHier

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to create initial hierarchy".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime

#Tracks the number of time hierarchy cleanup has yielded the same cleanup count
redundantCleanUpCount = 1
previousCleanUp = -1 # Tracks last cleanup count

# Loop through and eliminate the all redudant relationships then reclean until
# of relationships eliminated due to redundancy is 0, automatically ends after
# MAXREDUNDANT loop iterations yield the same # of redundant relations cleaned
# up to account for situations causing an endless loop
while True:
    redundantRelations = 0

    # Eliminate redundant relationships in the hierarchy
    for cui in translatedTopHier:
        ancestorList = []
        redundantRelations += reduceRedundancy(ancestorList, inProgressHier, \
                        cui, inProgressHier[cui], translatedLeaves)


    finishedHier = defaultdict(list) # will hold the final hierarchy

    # Re clean up relationships
    for cui in translatedTopHier:
        # Add holder entry to top tier concept
        if cui not in finishedHier:
            finishedHier[cui].append("holder")

        pathSoFar = [cui]

        cleanUpRelations(pathSoFar, translatedLeaves, cui, finishedHier, \
                         inProgressHier, cui, inProgressHier[cui] )

    inProgressHier = finishedHier


    # Break when no redudnant relations have been removed
    if redundantRelations is 0:
        break

    # Debug message that prints the number of relationships cleaned up due to
    # redundancy for each loop iteration
    if debugOn:
        logFile.write("Clean-up {} yielded {} redundant relations\n".format(\
            redundantCleanUpCount, redundantRelations))

    # Keeps track of number of cleanups yielding the same # of relationships
    # cleaned up.
    if redundantRelations == previousCleanUp:
        redundantCleanUpCount += 1
    else:
        redundantRelations = 0 # Reset redundant relations count

    # Break out of the loop after MAXREDUNDANT clean ups yielded same # of
    # removed relations
    if redundantCleanUpCount >= MAXREDUNDANT:
        # Print error message
        print "Error: Last {} clean-ups of the hierarchy removed the same\
            number of relationships. This most likely occurred due to a problem\
            with the inherent relationships in the database being used. There\
            is a chance that forward progress was being made during\
            these cleanUps; the limit can be increased by changing the\
            value of the MAXREDUNDANT variable in {} on line {}.".format(\
                    MAXREDUNDANT, FILENAME, LINENUMBER)

    # Update previousCleanUp count
    previousCleanUp = redundantRelations

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to finish cleaning the hieararchy".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime

# Write the relations to file in OWL format
writeToFile (translatedLeaves, finishedHier, configs['finalHierarchyFile'], \
             translatedTopHier, loopsDict)

# When debug mode is on, also write the initial hierarchy created before
# cleanup to a separate file
if debugOn:
    writeToFile (translatedLeaves, initialHierarchy,\
                configs['dirtyHierarchyFile'], translatedTopHier, loopsDict)

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to write hierarchy to file".format(\
                                                    currentTime - lastTime)
    lastTime = currentTime

# Log results
if debugOn:
    logFile.write("\nFinal RelationsDict: {}\n".format(str(relationsDict)))
    logFile.write("\nFinal translatedRelationsDict: {}\n".format(str(translatedDict)))
    logFile.write("\nFinal Leaves: {}\n".format(str(leaves)))
    logFile.write("\nFinal TranslatedLeaves: {}\n".format(str(translatedLeaves)))
    logFile.write("\nFinal loopsDict: {}\n".format(str(loopsDict)))
    logFile.write("\nFinal initialHierarchy: {}\n".format(str(initialHierarchy)))
    logFile.write("\nFinal finishedHier: {}\n".format(str(finishedHier)))
    logFile.write("\n\nLog finished : {}---------------------------------------------------" \
                "-----------------------------------------\n".format( \
                    datetime.today()))


# Close files
inFile.close()
topTierFile.close()
if debugOn:
    logFile.close()

# Close Cursor
cur.close()

#Close connection
cnx.close()

# Tracks time taken
if TIMETRACKING:
    currentTime = datetime.now()
    print "It took {} to finish remainder\nTook {} total for {} leaves".format(\
                    currentTime - lastTime, currentTime - startTime, len(leaves))
    lastTime = currentTime

