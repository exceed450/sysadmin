#!/bin/bash

#
# Filename: create_rpm_wrapper.sh
# Author: christian rustoeen
#
# Purpose: Wrapper for being able to create the rpm package  
# and update depot dev repositories in one go
#

app=$1

if [[ -z $1 ]] ; then
    echo "Usage: ./$0 <app>"
    exit 1
fi

su - chrisr -c "cd sym/packages; bash ./create_rpm_package.sh -a $app"
bash ./update_depot.sh $app

echo "================================================================="
echo "Please wait 15-30 minutes for the package to be updated in the   "
echo "production depot and available in the Red Hat Satellite server.  "
echo "================================================================="
echo
