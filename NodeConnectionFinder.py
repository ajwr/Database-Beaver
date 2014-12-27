import MySQLdb
import sys
from hierarchyBuilder import translateList

"""This program takes two nodes as input and returns the pathway (if it exists)
between the two nodes. Can be used for identifying problematic loops, etc.

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

DEBUGMODE = False

# Recursively Searches parents for a specific node. Saves the pathway taken.
def findNode (current, toFind, path, dbCursor):

    if current in path:
        return

    path = list(path)
    path.append(current)


    # Base Case
    if current == toFind:
        print "Relationship Pathway FOUND!"
        print "Pathway: {}".format(translateList(path, dbCursor))
        sys.exit()


    # Establish string for queries
    query = "SELECT CUI1, REL, CUI2, SAB from MRREL where CUI2 = '{}'" \
            "AND SAB = 'MTH' AND (REL = 'RN' OR REL = 'CHD')"

    # Establish connection and query MySQL database
    try:

        # Executue a query serach
        dbCursor.execute (query.format(current))

    # Catch errors from MySQL
    except MySQLdb.Error, e:
        try:
            # Prints the error
            print "MySQL Error [{}]: {} --- while querying {}".format(\
                                                e.args[0], e.args[1], current)

        except IndexError:
            # Prints the 1 argument error
            print "MySQL Error: {} --- while querying {}".format(str(e),\
                                                                current)

        sys.exit()

    # Fetch results of query
    rows = dbCursor.fetchall()

    # Process the resulting query
    for parent in rows:
        parentCUI = parent[0]
        rel = parent[1]
        childCUI = parent[2]
        sab = parent[3]

        if DEBUGMODE:
            print "Processing parentCUI ({}) and childCUI ({}) with REL ({}) and\
                SAB ({})".format (parentCUI, childCUI, rel, sab)

        findNode (parentCUI, toFind, path, dbCursor)



# Usage Message
if len(sys.argv) != 3:
    print "Usage: NodeConnectionFinder.py [leafCUI][rootCUI]"
    sys.exit()
else:
    leafCUI = sys.argv[1]
    rootCUI = sys.argv[2]

# Establish a connection and cursor to MySQL UMLS database
# Connect to MySQL server
try:
    cnx = MySQLdb.connect (host='localhost', user='umls1',\
                           port=3306, passwd='Umls12',\
                           db='UMLS')

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

pathway = list()

findNode (leafCUI, rootCUI, pathway, cur)

print "Leaf CUI {} not found".format(leafCUI)

