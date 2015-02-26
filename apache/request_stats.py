#!/usr/bin/env python

#
# Script for fetching usefull information from apache logs
#
import sys
import os
import re
import collections
import argparse

logfile_path = "access.log"

def slowest_requests():
    """ Count the number of slowest requests today """ 
    pattern_time_taken = "\.\w+\s(\d+)\s"
    pattern_request = "\"\w+\s([/\w+.-]+)"
    requests = {}

    try:
        logfile = open(logfile_path, "r")
        for line in logfile:
            match_time = re.search(pattern_time_taken, line)
            match_request = re.search(pattern_request, line)
            time_taken = match_time.group(1)
            request = match_request.group(1)
            requests[request] = time_taken
    except IOError:
        print "Error: Unable to read or open the file " + logfile_path

    sorted_requests = collections.Counter(requests)

    for req, time in sorted_requests.most_common(10000):
        print "Request: " + req + ", time taken: " + time

slowest_requests()

def num_req_vhost(vhost):
    """ Count the number of requests for a specific virtual host """
    num_requests = 0
    
    # we dont really need a more complicated regex to match this in an apache access.log file
    # even though we in theory could have provided a much better regex for matching domains
    pattern_vhost = "\"\s(" + vhost + ")"

    try:
        logfile = open(logfile_path, "r")
        for line in logfile:
            match = re.search(pattern_vhost, line)
            if match:
                num_requests = num_requests + 1
    except IOError:
        print "Error: Unable to read or open the file " + logfile_path

    print "Total number of requests for " + vhost + " is: " + str(num_requests)

def num_req_filetype(filetype):
    """ Count the number of requests that has a specific filetype """
    num_requests = 0
    pattern_filetype = "\"\w+\s[/0-9A-Za-z]+\.([\w+]+[.\w+]+)"

    try:
        logfile = open(logfile_path, "r")
        for line in logfile:
            match = re.search(pattern_filetype, line)
            if match:
                filetype_match = match.group(1)
                if (filetype == filetype_match):
                    if args.verbose:
                        print line
                    num_requests = num_requests + 1
    except IOError:
        print "Error: Failed to open or read the logfile " + logfile_path

    print "Total number of requests for " + filetype + " is " + str(num_requests)

def num_req_timeperiod(timeperiod):
    """ Count the number of requests between a specific time period """
    times = timeperiod.split("-")
    num_requests = 0
    fromTime = int(times[0].strip())
    toTime = int(times[1].strip())

    if toTime < fromTime:
        print "Error: function num_req_timeperiod requires that fromTime is less than toTime."
        sys.exit(1)

    match_time_pattern = "(\w\w\w\w):(\w\w):"

    try:
        logfile = open(logfile_path, "r")
        logfile_requests_path = "/tmp/request_stats_" + str(fromTime) + "_to_" + str(toTime) + ".log"

        if (os.path.isfile(logfile_requests_path)):
            os.remove(logfile_requests_path)

        logfile_requests = open(logfile_requests_path, "w")

        for line in logfile:
            match = re.search(match_time_pattern, line)
            pattern_hour = match.group(2)

            if int(pattern_hour) >= fromTime and int(pattern_hour) <= toTime:
                logfile_requests.write(line)
                num_requests = num_requests + 1

    except IOError:
        print "Error: Unable to read or open logfile " + logfile

    logfile_requests.close()
    logfile.close()
    print "Total requests between " + str(fromTime) + ":00 and " + str(toTime) + ":00 was " + str(num_requests) + "."
    print "Check the file " + str(logfile_requests_path) + " for information about all the requests that were made in this time period."
    print

def url_check(request):
    """ Count the number of times a specific url has been requested """
    request_count = 0
    pattern = "\s" + request

    try:
        logfile = open(logfile_path, "r")
        print "> Searching logfile for " + request + ", please wait..."
        for line in logfile:
            match = re.search(pattern, line)

            if match:
                request_count = request_count + 1

    except IOError:
        print "Error: Unable to read " + logfile

    print "Total number of requests to " + request + " is: " + str(request_count)
    print

def count_response_code(status):
    """ Count the requests which has a specific response code """
    status=status
    pattern = "\s[ " + str(status) + "]+\s"
    response_codes = 0

    try:
        logfile = open(logfile_path, "r")

        for line in logfile:
            match = re.search(pattern, line)
            if match:
                response_codes = response_codes + 1
    except IOError:
        print "An error occured trying to read the file " + logfile_path

    print "Total number of requests with " + str(status) + " response code: " + str(response_codes)

def top_requests():
    """ Check which IPs that are making the most requests """
    ip_pattern = "[0-9.]+[0-9.]+[0-9.]+[0-9.]+"
    ip_list = {}

    try:
        logfile = open(logfile_path, "r")
        for line in logfile:
            match = re.search(ip_pattern, line)
            if match:
                ip = match.group()
                if ip in ip_list:
                    ip_list[ip] = ip_list[ip] + 1
                else:
                    ip_list[ip] = 1

    except IOError:
        print "Ops, an error occured when trying to open " + logfile_path
        sys.exit(1)

    sorted_ips = collections.Counter(ip_list)

    print "Top 10 IPs making requests:"
    for ip, count in sorted_ips.most_common(10):
        print("IP: " + str(ip) + " has made " + str(count) + " request(s).")

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--num-req-timeperiod", help="Count number of requests between a specific time period. To check requests between 20:00 hours and 22:00 hours use the value '20 - 22'.")
parser.add_argument("-u", "--url-check", help="Count the number of times a specific url has been requested.")
parser.add_argument("-r", "--count-response-code", help="Count the number of requests for a specific response code.")
parser.add_argument("-t", "--top-requests", help="List which IPs that has made the most requests so far today.", action="store_true")
parser.add_argument("-v", "--verbose", help="Show more detailed information for an option.", action="store_true")
parser.add_argument("-f", "--num-req-filetype", help="Count the number of requests with a specific file type.")
parser.add_argument("-d", "--num-req-vhost", help="Count the number of requests for a specific vhost..")
args = parser.parse_args()

if not len(sys.argv) > 1:
    print "Usage error: One or more arguments are required, use the --help argument for usage information."

if args.num_req_timeperiod:
    timeperiod = args.num_req_timeperiod
    num_req_timeperiod(timeperiod)
elif args.url_check:
    url = args.url_check
    url_check(url)
elif args.count_response_code:
    response_code = args.count_response_code
    count_response_code(response_code)
elif args.top_requests:
    top_requests()
elif args.num_req_filetype:
    filetype = args.num_req_filetype
    num_req_filetype(filetype)
elif args.num_req_vhost:
    vhost = args.num_req_vhost
    num_req_vhost(vhost)

