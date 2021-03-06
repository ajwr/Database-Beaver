#!/usr/bin/python
import MySQLdb
import sys
import os
from datetime import datetime
from collections import defaultdict
from hierarchyBuilder import cleanUpRelations, writeToFile, reduceRedundancy, \
    areValidArguments, translateDictionary, translateList

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
    -x         = [Optional] Will enable debug mode  See the README file for
                 more information on debug mode.
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

# Timetracking Functionality
startTime = datetime.now()
lastTime = startTime # Time script was started, used to track progress
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
    print "\nIOError when trying to open configuration file ({}).".format(\
                                                        CONFIGURATIONFILE)
    sys.exit()
except NameError:
    print "\nNameError when trying to open configuration file ({}).".format(\
                                                        CONFIGURATIONFILE)
    sys.exit()

# Progress Message
sys.stdout.write( "Step 1 of 6: Establishing connection to database . . . ")


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
        print "\nError: {} not provided in configuration file.".format(attribute)

        #Print error message for config file format
        print """\nConfiguration file is improperly formatted.
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
    print "\nAn Error occurred while trying to open {}".format(\
                                            configs['inputCUIFile'])
    sys.exit()
try:
    topTierFile = open(configs['topLevelTierFile'], 'r')
except IOError, NameError:
    print "\nAn Error occurred while trying to open {}".format(\
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
if debugOn:
    currentTime = datetime.now()
    print "Took: {} ".format(currentTime - lastTime)
    lastTime = currentTime
else: # Print finish message
    print "Done!"

# Progress Message
sys.stdout.write("Step 2 of 6: Gathering Relationships . . . ")


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


# Establish string for queries
query = "SELECT CUI1, REL, CUI2, SAB, SUPPRESS from MRREL where CUI2 = '{}'" \
        "AND SAB = 'SNOMEDCT_US' AND (REL = 'RN' OR REL = 'CHD')"


# Relationship Harvesting: Loops through the Parent Queue making queries until
# all relationships relevant to the input CUIs are gathered
while True:
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
        continue

    # Process the resulting query
    for result in rows:
        # Assign information from query
        cui1 = result[0]
        rel = result[1]
        cui2 = result[2]
        sab = result[3]
        suppress = result[4]

        # Skip inactive relationships (obsolete or due to SAB,TTY or editor)
        if suppress == 'O' or suppress == 'Y' or suppress == 'E':
            continue

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
if debugOn:
    currentTime = datetime.now()
    print "Took: {}".format(currentTime - lastTime)
    lastTime = currentTime
else:
    print "Done!"

# If debugging is on, translate the dictionaries and lists prematurely
if debugOn:
    sys.stdout.write( "Step 2.5 of 6: Translating Relations (DEBUG MODE) . . . ")
    topTier = translateList( topTier, cur )
    relationsDict = translateDictionary( relationsDict, cur )
    leaves = translateList( leaves, cur )
    currentTime = datetime.now()
    print "Took: {}".format(currentTime - lastTime)
    lastTime = currentTime

# Progress Message
sys.stdout.write("Step 3 of 6: Building Initial Hierarchy . . . ")


# Will hold the hierarchy while being built and cleaned up
inProgressHier = defaultdict(list)

# Keeps tracks of loops encountered
loopsDict = defaultdict(list)


# Create the initial hierarchy, by following pathways from topTier CUIs
for parentCui in topTier:
    # Save parent and child for traversal
    if (relationsDict.has_key(parentCui)):
        childList = relationsDict[parentCui]
    else:
        continue

    # Add the Top Level Concept to the dictionary
    inProgressHier[parentCui].append("holder")
    pathSoFar = [parentCui]
    cleanUpRelations(pathSoFar, leaves, parentCui, inProgressHier,\
                      relationsDict, parentCui, childList, loopsDict)

# Save the initial hierarchy created pre-cleanup if debug is on
if debugOn:
    initialHierarchy = inProgressHier

# Tracks time taken
if debugOn:
    currentTime = datetime.now()
    print "Took: {}".format(currentTime - lastTime)
    lastTime = currentTime
else:
    print "Done!"

# Progress Message
sys.stdout.write("Step 4 of 6: Cleaning the Hierarchy . . . ")

#Tracks the number of time hierarchy cleanup has yielded the same cleanup count
redundantCleanUpCount = 1
previousCleanUp = -1 # Tracks last cleanup count

# Loop through and eliminate the redundant relationships then reclean until
# of relationships eliminated due to redundancy is 0, automatically ends after
# MAXREDUNDANT loop iterations yield the same # of redundant relations cleaned
# up to account for situations causing an endless loop
while True:
    redundantRelations = 0

    # Eliminate redundant relationships in the hierarchy
    for cui in topTier:
        ancestorList = []
        redundantRelations += reduceRedundancy(ancestorList, inProgressHier, \
                        cui, inProgressHier[cui], leaves)


    finishedHier = defaultdict(list) # will hold the final hierarchy

    # Re clean up relationships
    for cui in topTier:
        # Add holder entry to top tier concept
        if cui not in finishedHier:
            finishedHier[cui].append("holder")

        pathSoFar = [cui]

        cleanUpRelations(pathSoFar, leaves, cui, finishedHier, \
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
if debugOn:
    currentTime = datetime.now()
    print "Took: {}".format(currentTime - lastTime)
    lastTime = currentTime
else:
    print "Done!"

# Progress Message
sys.stdout.write("Step 5 of 6: Translating Final Hierarchy . . . ")

# Translate the finished hierarchy, leaves, and topHierarchy before writing
# it to the output file
if not debugOn:
    translatedLeaves = translateList (leaves, cur)
    translatedFinishedHier = translateDictionary (finishedHier, cur)
    translatedTopTier = translateList (topTier, cur)
    translatedLoopsDict = translateDictionary (loopsDict, cur, True)
else:
    translatedLeaves = leaves
    translatedFinishedHier = finishedHier
    translatedTopTier = topTier
    translatedLoopsDict = loopsDict

# Tracks time taken
if debugOn:
    currentTime = datetime.now()
    print "Took: {}".format(currentTime - lastTime)
    lastTime = currentTime
else:
    print "Done!"

# Progress Message
sys.stdout.write("Step 6 of 6: Writing Hierarchy to File . . . ")

# Write the relations to file in OWL format
writeToFile (translatedLeaves, translatedFinishedHier,\
             configs['finalHierarchyFile'], translatedTopTier,\
             translatedLoopsDict)

# When debug mode is on, also write the initial hierarchy created before
# cleanup to a separate file
if debugOn:
    translatedInitialHierarchy = translateDictionary(initialHierarchy, cur)
    writeToFile (translatedLeaves, translatedInitialHierarchy,\
                configs['dirtyHierarchyFile'], translatedTopTier,\
                translatedLoopsDict)

# Tracks time taken
if debugOn:
    currentTime = datetime.now()
    print "Took: {}".format(currentTime - lastTime)
    lastTime = currentTime
else:
    print "Done!"

# Log results
if debugOn:
    logFile.write("\nFinal RelationsDict: {}\n".format(str(relationsDict)))
    logFile.write("\nFinal TranslatedRelationsDict: {}\n".format(\
            str(translateDictionary(relationsDict, cur))))
    logFile.write("\nFinal Leaves: {}\n".format(str(leaves)))
    logFile.write("\nFinal TranslatedLeaves: {}\n".format(\
            str(translatedLeaves)))
    logFile.write("\nFinal loopsDict: {}\n".format(str(translatedLoopsDict)))
    logFile.write("\nFinal TranslatedInitialHierarchy: {}\n".format(\
            str(translatedInitialHierarchy)))
    logFile.write("\nFinal FinishedHier: {}\n".format(\
            str(translatedFinishedHier)))
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
if debugOn:
    currentTime = datetime.now()
    print "Took {} total for {} leaves".format(\
        currentTime - startTime, len(leaves))

print "Finished!"
