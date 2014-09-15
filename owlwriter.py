"""Module containing the ontology class for writing hierarchies in OWL format

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
class ontology:
    """Class for creating the OWL file for use with Protege"""

    # Initialize the ontology object with the file to write to
    def __init__(self, filename):
        """Initialize the ontology object. Opens the file to write the hierarchy
        to.

        Input:
            filename: String naming the file to be used for saving the final
                      hierarchy to.

        """
        self.outfile = open(filename, 'w')

    # Write the version header
    def version (self, version):
        """Write the version header to the outfile

        Input:
            version: The current version of xml being used
        """
        self.outfile.write('<?xml version="{}"?>\n\n'.format(version))

    # Write the doctype header
    def doctype(self):
        """Writes the doctype header"""
        self.outfile.write(
            '<!DOCTYPE rdf:RDF [\n' \
            '    <!ENTITY owl "http://www.w3.org/2002/07/owl#" >\n' \
            '    <!ENTITY xsd "http://www.w3.org/2001/XMLSchema#" >\n' \
            '    <!ENTITY rdfs "http://www.w3.org/2000/01/rdf-schema#" >\n' \
            '    <!ENTITY rdf "http://www.w3.org/1999/02/22-rdf-syntax-ns#" >\n' \
            ']>\n\n')

    # Write the rdfHeader
    def rdfHeader(self, ontologyIRI):
        """Writes the rdfHeader to the file.

        Input:
            ontologyIRI: The IRI of the ontology being constructed

        """

        # Save the ontologyIRI
        self.iri = ontologyIRI
        self.outfile.write (
            '<rdf:RDF xmlns="{}#"\n'.format(ontologyIRI))

        self.indent(5)

        self.outfile.write ('xml:base="{}"\n'.format(ontologyIRI))

        self.indent(5)

        self.outfile.write(
            'xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"\n' \
            '     xmlns:owl="http://www.w3.org/2002/07/owl#"\n' \
            '     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"\n' \
            '     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n')

        self.indent()

        self.outfile.write(
            '<owl:Ontology rdf:about="{}"/>\n\n\n\n'.format(ontologyIRI))

    # Write out the classes header
    def classes(self):
        """Writes out the classes header"""
        self.indent()
        self.outfile.write("<!--\n")
        self.outfile.write("    ///////////////////////////////////////////////////////////////////////////////////////\n")
        self.outfile.write("    //\n" \
                          '    // Classes\n' \
                          '    //\n' \
                          '    ///////////////////////////////////////////////////////////////////////////////////////\n'
                          '     -->\n\n\n')



    # Adds all the classes contained in the dictionary to the file
    def addClass (self, child, parentList):
        """Writes all the classes contained in the dictionary to the file

        Input:
            child: The cui-name of the current child being written to the file
            parentList: List of parents of the child passed in
        """

        # Add comment header
        self.indent()
        self.outfile.write('<!-- {}#{} -->\n\n'.format(self.iri, \
                                        child))

        self.indent()
        # Add Class entry
        self.outfile.write('<owl:Class rdf:about="{}#{}">\n'.format(self.iri,\
                                                                child))

        # Add each parent to the child class
        for parent in parentList:
            if parent == 'none':
                continue
            self.indent(8)
            # Add subclasses
            self.outfile.write(
                '<rdfs:subClassOf rdf:resource="{}#{}"/>\n'.format(self.iri,\
                    parent.replace(' ', '_').replace('(', '').replace(')', '').\
                    replace(',', '').replace("\'", '').replace("\"", '').\
                    replace("[","").replace("]", "").replace("&", "and")))

        self.indent()
        # End class definition
        self.outfile.write('</owl:Class>\n\n\n\n')


    # Ending XML entity structure and close the output file
    def end(self):
        """Writes the ending XML entity structure"""

        self.outfile.write('</rdf:RDF>')

        self.outfile.close()


    # Indents either a passed number of spaces, or 4 as default
    def indent(self, count=4):
        """Indents either a passed in number of spaces, or 4 as default

        Input:
            count: [Optional] Number of spaces to indent by. Default is 4.

        """

        while count > 0:
            self.outfile.write(" ")
            count = count-1
