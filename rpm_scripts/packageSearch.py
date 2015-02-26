#!/local/bin/python -tt
#
# packageSearch.py
#
# author: christian rustoeen <chrisr@basefarm.no> - System manager
#
# Search for a package and print information about it if the package version is in between the
# version numbers specified by the user on the command line and send an e-mail to the employees
# that are technical resposible for the server where the package version is found
#

#
# Needs a few adjustments in order to work in specific environments
#

import ldap
import xmlrpclib
import re
import pprint
import os
import smtplib
import sys
import argparse
from distutils.version import StrictVersion

# ldap settings
ldap_server = ""
base_search_osl = ""
base_search_sth = ""
base_search_ams = ""
attributes = "" 
mail_server = ""

# satellite settings
satellite_url = ""
satellite_username = ""
satellite_password = ""
specific_package_ids = []
total_installations = []
client = xmlrpclib.Server(satellite_url, verbose=0)
key = client.auth.login(satellite_username, satellite_password)

#  file settings
file_path = "/tmp/"
package_count_all = {}
file_multiple_installations = file_path + "multiple_installations"

# Misc. data structures for temp data storage
tomcat_install_pattern = "tomcat[-0-9]?$"
errors = []
tka_email_list = []
customer_packages = {}
customer_specific_packages = {}
multi_install = {}
customer_mail = {}

# count variables
osl_package_count = 0
sth_package_count = 0
ams_package_count = 0
packages = []

# Create the argument parser
arguments = argparse.ArgumentParser(description="Specify package and package versions to search for.")
arguments.add_argument("--package", "-p", action="store", nargs=1,
                       required=True, help="Specify an application to search for.")
arguments.add_argument("--from-version", "-f", action="store", nargs=1, help="Specify the package version to search from.")
arguments.add_argument("--to-version", "-t", required=True, action="store", nargs=1, help="Specify the package version to search to.")
arguments.add_argument("--detail", "-c", action="store_true", help="Output additional information about the installations, usefull to see for example how many installations exist in a given country.")
arguments.add_argument("--cve", "-s", action="store", nargs="*", help="Specify the CVE codes for the vulnerabilities.")
arguments.add_argument("--vulnerable-version", "-r", nargs="*", help="Specify the vulnerable software versions.")
arguments.add_argument("--severity", "-e", action="store", help="Specify the severity of the vulnerability.")
arguments.add_argument("--upgrade-version", "-u", action="store", nargs=1, help="Specify version users should upgrade to.")
arguments.add_argument("--satellite", "-a", action="store", nargs=1, help="Query Red Hat Satellite server.")
arguments.add_argument("--ldap", "-l", action="store", nargs=1, help="Query DAM/LDAP.")

# Check if we should query satellite or LDAP
if ldap:
    query_ldap=True
elif satellite:
    query_ldap=False
else:
    print "Usage error: You need to specify either --ldap or --satellite, use -h to get more information."

# Parse the command-line arguments
parsed_arguments=arguments.parse_args()

package = parsed_arguments.package[0]
from_version = parsed_arguments.from_version[0]
to_version = parsed_arguments.to_version[0]
detail=parsed_arguments.detail

# fetch a list of vulnerable software versions
if parsed_arguments.vulnerable_version:
    vulnerable_version=""
    for version in parsed_arguments.vulnerable_version:
        if not vulnerable_version:
            vulnerable_version=version
        else:
            vulnerable_version=vulnerable_version + " ," + version

# fetch a list of cves
if parsed_arguments.cve:
    cve=""
    for cve_arg in parsed_arguments.cve:
        cve=cve + " " + cve_arg

if parsed_arguments.severity:
    severity=parsed_arguments.severity

if parsed_arguments.upgrade_version:
    upgrade_version=parsed_arguments.upgrade_version[0]

### SATELLITE FUNCTIONS
def search_package(package, satellite_connection, satellite_connection_auth):
    """ Search for a package in Red Hat Satellite server """
    package_sat_result = satellite_connection.packages.search.name(satellite_connection_auth, package)
    return package_sat_result

def find_specific_versions(package, satellite_connection, satellite_connection_auth):
    """ Display specific versions of a package in Red Hat Satellite server """
    package_sat_result = search_package(package, satellite_connection, satellite_connection_auth)
    for pack in package_sat_result:
        try:
            if StrictVersion(pack['version']) >= from_version and StrictVersion(pack['version']) <= to_version:
                check_name = re.search(tomcat_install_pattern, pack['name'])
                if (check_name):
                    specific_package_ids.append(pack['id'])
                    system = satellite_connection.system.listSystemsWithPackage(satellite_connection_auth, pack['id'])
                    for sys in system:
                        total_installations.append(sys)
        except ValueError:
            pass
        
        return total_installations

### LDAP FUNCTIONS
def create_ldap_connection(server):
    """ Create and return an LDAP connection """
    ldap_con=ldap.initialize(ldap_server)
    return ldap_con

def search_ldap(connection, search_base, attrlist):
    """ Execute a search in LDAP """
    if (connection and search_base):
        if (attrlist):
            ldap_result = connection.search_s(search_base, ldap.SCOPE_SUBTREE, attrlist=attrlist)
        else:
            ldap_result = connection.search_s(search_base, ldap.SCOPE_SUBTREE) 
    else:
        print "Error: search_ldap: Connection object or search base argument given was not valid."
        print
        sys.exit(1)

    return ldap_result

def parse_package_data(ldap_result, application, location):
    """
    Parse package information from LDAP and print all packages
    that has a version that is between the arguments on the command line
    """
    # count the total number of packages
    package_count=0

    file_package_file=file_path + location
    
    # count the number of packages for each country
    file_packages=open(file_package_file, "w+")

    # count the number of installations where the package is installed
    # with multiple versions on the same server
    file_installations=open(file_multiple_installations + "_" + location, "w+")
    
    # count the number of servers that has multiple installations of a package
    multi_install_count=0
    
    # Iterate through all packages on servers in osl
    for inventory_row, inventory_attributes in ldap_result:
        if 'DAMswPackageUsed' in inventory_attributes:
            check_inventory(inventory_row, inventory_attributes, multi_install_count)
    
def check_inventory(inventory_entries, inventory_attributes, multi_install_count):
    """ Check an inventory in DAM for a specific package """
    server = inventory_entries
    try:
        for inventory_entry in inventory_attributes['DAMswPackageUsed']:
            if (re.search(package + "[0-9]?-[0-9]+", inventory_entry)):
                package_info=search_ldap(ldap_connection, inventory_entry, ['DAMswPackageVersion', 'DAMswPackageName'])
                check_package(package_info, server, inventory_entry, inventory_attributes)
    except ldap.NO_SUCH_OBJECT:
        errors.append("There was a problem with " + package + "\n on " + server + ", this package does not exist anymore in LDAP.")

def check_package(package_info, server, inventory_entry, inventory_attributes):
    """ Check if a package in an inventory in DAM is between two versions """
    for package_ent, pack_ent_attributes in package_info:
        package_name = 
        package_version = pack_ent_attributes['DAMswPackageVersion'][0]
    
        if StrictVersion(package_version) >= from_version and StrictVersion(package_version) <= to_version:
            return True

### COMMON FUNCTIONS
def find_tka(server):
    """ 
    Find a TKA, customer name and customer shortname for a specific server 
    and return a dict with that information 
    """
    server_info = search_ldap(ldap_connection, server, ['owner'])
    
    for server_entry, owner in server_info:
        owner_object = owner['owner'][0]
    
    owner_info = search_ldap(ldap_connection, owner_object, ['owner', 'o', 'orguid', 'DAMcontactPerson'])

    for owner_row, owner_attributes in owner_info:
        customer_object=owner_attributes['orguid'][0]
        customer_name=owner_attributes['o'][0]
        tka_object=owner_attributes['DAMcontactPerson'][0]
        tka_info=search_ldap(ldap_connection,tka_object,['mail'])
   
    for tka_info_row, tka_info_attributes in tka_info:
        tka_mail=tka_info_attributes['mail']
    
    customer_string = customer_name
    mail = tka_mail[0]
    customer = customer_object
    tka_info['shortname'] = customer_string
    tka_info['customer'] = customer
    tka_info['mail'] = mail

    return tka_info

def inform_tka(customer_string, mail, customer, package_name, package_version):
    """ Inform a TKA about a vulnerability """
    if customer not in customer_packages.keys():
        customer_packages[customer] = dict()
        customer_packages[customer]['mail'] = mail
        customer_packages[customer]['name'] = customer_string
        customer_packages[customer][server] = package_name + " " + package_version
        package_count=package_count+1
    
    send_mail(mail, customer)

def send_mail(mail, customer):
    """ Send an e-mail """
    if severity and cve and vulnerable_version:
        print "-> Sending information about the vulnerability..."
        for customer_entry, package_attributes in customer_packages.iteritems():
            customer_name=package_attributes['name']
            mail_body=[]
            server_list=[]
            mail_body.append("You are receiving this e-mail because you are listed in Basefarm' systems as the Technical Account Manager ")
            mail_body.append("for " + customer_name + ".\n")
            mail_body.append("A " + severity + " security vulnerability has been found in " + package + " version " + vulnerable_version + ".\n")
            mail_body.append("For more information see: " + cve + " at https://cve.mitre.org/\n")
            mail_body.append("This is a list of the servers for " + customer_name + " running the vulnerable version:")
           
            for server_name, package_version in package_attributes.iteritems():
                if server_name == "name" or server_name == "mail":
                    continue
                server_list.append(server_name + ": " + package_version)
            server_info=""

            for server in server_list:
                server_info = server_info + "\n" + server
            mail_body.append(server_info)
            mail_body.append("\nYou are advised to upgrade to version " + upgrade_version + " of the software as soon as possible.")
            mail_body.append("\n- System manager for " + package)

            content=""
            for line in mail_body:
                content = content + "\n" + line

            subject = "Security alert"
            mail = "Subject: %s\n\n%s" % (subject, content)

            print "--> Sending mail to technical account manager for " + customer_name
            to_mail=""
            from_mail=""
            content_mail = mail_body
            #smtp_server = smtplib.SMTP(mail_server)
            #smtp_server.sendmail(from_mail, to_mail, mail)
            #smtp_server.quit()
            print "-> Mail sent."
            print
    else:
        print "User did not specify enough vulnerability information about the software, showing a count of packages between " + str(from_version) + " and " + str(to_version) + " found."

print
print "[ Searching for " + str(package) + " packages in DAM between package versions " + str(from_version) + " and " + str(to_version) + " ]"
print

# Create the connection
ldap_connection=create_ldap_connection(ldap_server)
print "-> Searching for " + str(package) + " packages on servers in oslo, please wait..."

# check the packages for servers in osl
search_osl=search_ldap(ldap_connection, base_search_osl, attributes)
parse_package_data(search_osl, package, "osl")
print "-> Searching for " + package + " packages on servers in stockholm, please wait..."

# check the packages for servers in sth
search_sth=search_ldap(ldap_connection, base_search_sth, attributes)
parse_package_data(search_sth, package, "sth")

print "-> Searching for " + package + " packages on servers in amsterdam, please wait..."
print

# check the packages for servers in ams
search_ams=search_ldap(ldap_connection, base_search_ams, attributes)
parse_package_data(search_ams, package, "ams")

if errors:
    print "The following errors were encountered during the search:"
    for error in errors:
        print error
    print

