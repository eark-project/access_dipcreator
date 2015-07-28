# coding=UTF-8
'''
Created on Mar 2, 2015

@author: Jan Rörden (based on: http://alex-sansom.info/content/validating-xml-against-xml-schema-python)
@author: Sven Schlarb
'''

import hashlib
import unittest

import lxml
from lxml.etree import XMLSyntaxError

from config import log

import config.params

from lib.xml.XmlValidation import XmlValidation
from lib.fixity.ChecksumAlgorithm import ChecksumAlgorithm
from lib.fixity.ChecksumValidation import ChecksumValidation
from lib.metadata.mets.MetsValidation import MetsValidation
from lib.metadata.mets.ParsedMets import ParsedMets

class SIPDeliveryValidation(object):
    """
    SIP delivery validation
    """

    _logger = log.init('sip-to-aip-converter')

    # Clear any previous errors
    lxml.etree.clear_error_log()

    def validate_delivery(self, deliveryDir, delivery_xml_file, schema_file, package_file):
        """
        Validate the delivery METS document. Does XML validation of the delivery METS file and fixity check on file
        level.

        @type       deliveryDir: string
        @param      deliveryDir: Path to delivery directory
        @type       delivery_xml_file:  string
        @param      delivery_xml_file:  Path to delivery METS file.
        @type       package_file:  string
        @param      package_file:  Path to package file file (e.g. TAR).
        @rtype:     bool
        @return:    Validity of delivery
        """
        valid_xml = False
        valid_checksum = False
        self._logger.info("Validating delivery: %s using schema: %s and package file %s" % (
            delivery_xml_file, schema_file, package_file))

        try:
            # Parse the XML file, get the root element
            parsed_mets = ParsedMets(deliveryDir)
            parsed_mets.load_mets(delivery_xml_file)

            # If the XSD file wasn't found, extract location from the XML
            if schema_file == None:
                schema_file = parsed_mets.get_mets_schema_from_schema_location()

            # Parse the XSD file
            parsed_sfile = lxml.etree.parse(schema_file)

            # Validate the delivery XML file
            xmlVal = XmlValidation()
            valid_xml = xmlVal.validate_XML(parsed_mets.mets_tree, parsed_sfile)

            # Checksum validation
            checksum_expected = ParsedMets.get_file_element_checksum(parsed_mets.get_first_file_element())
            checksum_algorithm = ParsedMets.get_file_element_checksum_algorithm(parsed_mets.get_first_file_element())
            csval = ChecksumValidation()
            valid_checksum = csval.validate_checksum(package_file, checksum_expected, ChecksumAlgorithm.get(checksum_algorithm))

            # Mets validation
            mval = MetsValidation(parsed_mets)
            valid_files_size = mval.validate_files_size()

            return (valid_xml and valid_checksum and valid_files_size)

        except (XMLSyntaxError), why:
            self._logger.error('Error validating delivery %s, why: %s' % (delivery_xml_file, str(why)))
            return False


class TestSIPDeliveryValidation(unittest.TestCase):

    _logger = log.init('sip-to-aip-converter')

    delivery_dir = config.params.root_dir + '/test/resources/Delivery-test/'

    schema_file = delivery_dir + 'schemas/IP_CS_mets.xsd'
    package_file = delivery_dir + 'SIP-sqldump.tar.gz'
    vsip = SIPDeliveryValidation()

    def test_validate_delivery(self):
        """
        Delivery must be valid if all validation tests succeed
        """
        delivery_file = self.delivery_dir + 'Delivery.SIP-sqldump.xml'
        actual = self.vsip.validate_delivery(self.delivery_dir, delivery_file, self.schema_file, self.package_file)
        self.assertTrue(actual, "Delivery must be valid if all validation tests succeed")


if __name__ == '__main__':
    unittest.main()