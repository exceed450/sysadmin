#!/local/bin/python

#
# Filename: MultiRemoteTask.py
# Author: Christian Rustooen <chrisr@basefarm.no>
# Purpose: Run any command or script on any number of servers using ssh public key authentication
#
# Please note: 
# This script is under git version control. You should never modify this script without using git.
# If you want to modify it, then create a copy of the script and start modifying that way.
#

# os - needed to expand the private key in the transferFile method.
# sys - needed to exit the script when necessary
# paramiko - the module that provides the ssh functionality
# argparse - command-line argument parsing
# time - used to sleep in various methods to wait for data in a correct way
import os
import sys
import paramiko
import argparse
import time

# This script doesnt really benefit much from the OOP way of coding but its a
# little cleaner, easier to work with and easier to expand. It probably should
# and should be sorted out into different modules for connecting, transfering
# files and executing commands, but that will be a subject for a future version
# of the script
class MultiTaskRemote(object):
    hostname = None
    hostfile = None
    hostFileCheck = None
    scriptname = None
    command = None

    def __init__(self):
        parser = argparse.ArgumentParser(description="This script is used to run any number of scripts or commands on any number of servers by using ssh public key authentication.")
        parser.add_argument('--hostname', nargs="+", help="Specifies hostname(s) to run the command or script on.", metavar="<hostname>", dest="hostname")
        parser.add_argument('--command', nargs="+", help="Specifies the command to run on the remote host(s).", metavar="<command>", dest="command")
        parser.add_argument('--hostfile', nargs=1, help="Specifies hostfile to read hostnames from.", dest="hostfile")
        parser.add_argument('--scriptname', nargs="+", help="Specifies the name of the script to transfer to the hostname(s).", dest="scriptname")
        parser.add_argument('--remotepath', nargs=1, help="Specifies the remote path (directory) to transfer the script to on the remote server (for example /tmp).", dest="remoteFilePath")
        parser.add_argument('--interpreter', nargs=1, help="Specifies the interpreter used for executing the script on the remote host. Some filestypes are checked automatially by the script so you might not need to specify this.", dest="interpreter")
        arguments = parser.parse_args()

        # Verify that we have valid data from the command-line.
        if (arguments.hostname and arguments.hostfile):
            print "Usage error: You cannot use both --hostname and --hostfile together."
            print "Use the --help argument to display the help menu."
        elif not (arguments.hostname or arguments.hostfile):
            print "Usage error: You have to specify either a hostname or a file which contains a list of hostnames."
            print "Use the --help argument to display the help menu."
        elif not (arguments.command or arguments.scriptname):
            print "Usage error: You have to specify either a command or a scriptname to run."
            print "Use the --help argument to display the help menu."

        if (arguments.hostname):
            hostFileCheck = False
        elif (arguments.hostfile):
            hostFileCheck = True

        # If we have valid data then run the appropriate methods
        if (arguments.command):
            if (hostFileCheck):
                if (len(arguments.hostfile) > 1):
                    print "Usage error: You can only specify one filename to read the host data from."
                    sys.exit(1)

                self.initRun(arguments.command, arguments.hostfile, hostFileCheck)
            elif (arguments.hostname):
                self.initRun(arguments.command, arguments.hostname, hostFileCheck)
        elif (arguments.scriptname):
            if (arguments.remoteFilePath):
                if (arguments.hostfile):
                    self.initScript(arguments.scriptname, arguments.hostfile, hostFileCheck, arguments.remoteFilePath, arguments.interpreter)
                else:
                    self.initScript(arguments.scriptname, arguments.hostname, hostFileCheck, arguments.remoteFilePath, arguments.interpreter)
            else:
                print "Usage error: You must specify a remote path (--remotepath) when using the --scriptname option like for example /tmp. This path is where the script will be transfer to on the remote server."


    def initRun(self, command, hostdata, hostFileCheck):
        if (hostFileCheck):
            hostInfoFile = open(hostdata[0])
            self.executeCommand(command, hostInfoFile)
        else:
            self.executeCommand(command, hostdata)

    
    def executeCommand(self, command, hostdata):
        sshCon = paramiko.SSHClient()
        sshCon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        for host in hostdata:
            print

            # Connect to the host in question and create an interactive SSH session
            # Putting this in its own function doesnt work, when the ssh session object is returned to 
            # this function the ssh session, for some reason, is closed and has status disconnected.
            # Interactive-shell session is used for being able to execute privileged commands if specified
            try:
		# make sure to strip the newline at the end of the hostname or it wont be parsed by python correctly
		host = host.rstrip("\n")
                sshCon.connect(host)
                interactiveSSH = sshCon.invoke_shell("vt100", 80, 50)
            except paramiko.SSHException:
                print "ERROR: Could not connect to " + host.rstrip("\n")
                print "This script requires that you have an ssh private key on this server in addition to a corresponding public key on all remote hosts."
            else:
		print "- Connected to " + host

                # Execute all commands on the command-line on the host
                for cmd in command:
                    try:
                        # Check if data is ready to be sent
                        i=0
                        while (i < 10):
                            if (interactiveSSH.send_ready()):
                                interactiveSSH.send(cmd + "\n")
                                print "-- Executing command '" + cmd + "' on " + host + " ..."
                                print
                                i=10
                            else:
                                print "-- Waiting for server to accept data ..."
                                time.sleep(1)
                                i=i+1
                                if (i == 10):
                                    print "ERROR: Timed out after 10 tries. Server is not responding."
                        
                        i=0
                        # Check if data is ready to be read
                        while (i < 2):
                            if not (interactiveSSH.recv_ready()):
                                time.sleep(1)
                                i=i+1
                            else:
                                data = interactiveSSH.recv(1024)
                                print data
                                i=0
	
                    # If we fail to execute the command, raise an exception and show a stacktrace
                    except paramiko.SSHException:
                        print "ERROR: Failed to execute the command " + cmd
                        print
                print "========================================================"
                print
	
    
    def transferFile(self, host, scriptname, remoteFilePath):
		host = host
		port = 22

		# Establish the connection and transfer the file
		transport = paramiko.Transport((host, port))
		privatekeyfile = os.path.expanduser('~/.ssh/id_rsa')
		key = paramiko.RSAKey.from_private_key_file(privatekeyfile)
		try:
			transport.connect(username="zenoss",pkey = key)
			print "- Transfering script"
			sftp = paramiko.SFTPClient.from_transport(transport)

			localpath = scriptname
			remotepath = remoteFilePath[0] + "/" + scriptname

			sftp.put(localpath, remotepath)

			sftp.close()
			transport.close()
		except paramiko.AuthenticationException:
			print "ERROR: Failed to connect to " + host + "."
			print "This probably is because you dont have ssh public key authentication set up correctly.."
			print
			
			# We have a failure
			return 0
		else:
		    print "-- Successfully transfered script"

		# Everything went OK
		return 1


    # NOTE for next version of the script:
    # this function in addition to the transferFile function supports executing
    # any number of script on any number of servers but when executing more than
    # more script on a server it isnt yet much efficient. need to implement a
    # for loop in the transferFile function to make it transfer all scripts
    # before starting to execute them

    # NOTE for next version of the script:
    # remotePath should not be required anymore but you should still be able to 
    # set it using an argument. By default it should be /tmp since everyone can
    # write to this directory. The script should also clean up after itself by
    # deleting the script after i has been run
    def executeScript(self, scriptname, hostdata, remoteFilePath, interpreterExec):
        for host in hostdata:
            print
            host = host.rstrip("\n")
	    print host

            for script in scriptname:
                if (self.transferFile(host, script, remoteFilePath)):
                    cmd = interpreterExec + " " + remoteFilePath[0] + "/" + script
                else:
                    print "Error: Failed to transfer script to remote host, checking if there is any additional hosts to transfer and run the script on"
                    break
            
                sshCon = paramiko.SSHClient()
                sshCon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
                # Connect to the host in question and create an interactive SSH session
                # Putting this in its own function doesnt work, when the ssh session object is returned to 
                # this function the ssh session, for some reason, is closed and has status disconncted.
                try:
                    sshCon.connect(host)

                    # Interactive-shell session for being able to execute privileged commands
                    interactiveSSH = sshCon.invoke_shell("vt100", 80, 50)
            
                except paramiko.SSHException:
                    print "ERROR: Could not connect to " + host.rstrip("\n")
            
                try:
                    # Check if data is ready to be sent
                    i=0
                    while (i < 10):
                        if (interactiveSSH.send_ready()):
                            interactiveSSH.send(cmd + "\n")
                            print "--- Executing script"
                            i=10
                        else:
                            print "-- Waiting for server to run script ..."
                            time.sleep(1)
                            i=i+1
                        
                            if (i == 10):
                                print "ERROR: Timed out after 10 tries. Server is not responding, exiting."
                                sys.exit(1)

                    i=0
                    # Check if data is ready to be read
                    while (i < 5):
                        if not (interactiveSSH.recv_ready()):
                            time.sleep(1)
                            i=i+1
                        else:
                            data = interactiveSSH.recv(1024)
                            print data.strip("\n")
                            i=0
                    
                    # If we fail to execute the command, raise an exception and show a stacktrace
                except paramiko.SSHException:
                    print "ERROR: Failed to execute the script " + cmd + "."
                    print
            
                print "========================================================"
                print


    # NOTE for next version of the script:
    # There almost always is an interpreter defined in the script file, it
    # should be checked if you can use that interpreter first and if there isnt
    # an interpreter specified in the script then use the code below or write
    # better code to check which interpreter that should be used
    def initScript(self, scriptname, hostdata, hostFileCheck, remoteFilePath, interpreter):
        if (interpreter):
            interpreterExec=interpreter[0]
        else:
            if (scriptname[0].endswith(".sh")):
                interpreterExec="/local/gnu/bin/bash"
            elif (scriptname[0].endswith(".pl")):
                interpreterExec="/local/bin/perl"
            elif (scriptname[0].endswith(".py")):
                interpreterExec="/local/bin/python"
            elif (scriptname[0].endswith(".groovy")):
                interpreterExec="/local/bin/groovy"
	    else:
		print "ERROR: Unable to identify the type of script provided."
		print "There is automatic support for : shell, python, perl or groovy script."
		print "Use the --interpreter argument to run a different type of script."
		print
		sys.exit(1)

        if (hostFileCheck):
            hostInfoFile = open(hostdata[0])
            self.executeScript(scriptname, hostInfoFile, remoteFilePath, interpreterExec)
        else:
            self.executeScript(scriptname, hostdata, remoteFilePath, interpreterExec)

