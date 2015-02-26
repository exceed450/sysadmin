#!/bin/bash

# $Id: create_rpm_package.sh,v 1.2 2014/06/13 13:39:05 chrisr Exp $

#
# Filename: create_rpm_spec.sh
# Purpose: Create an rpm from a binary software distribution
# Author: christian rustoeen
#

#
# Do not modify this script
# If you for some good reason need to modify it then create
# a copy of it and then do your changes.
#

# Check for required arguments
while getopts ":a:" opt; do
  case $opt in
    a)
      app=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Error: Option -$OPTARG requires an argument." >&2
      echo "Usage: ./$0 -a <app>"
      echo
      exit 1
      ;;
  esac
done

if [[ -z $app ]] ; then
    echo "Error: Not enough arguments given."
    echo "Usage: ./$0 -a <app>"
    echo
    exit 1
fi

spec_file_settings="create_rpm_spec.settings"
source_url_by_user=0
build_package="rpmbuild -ba"
home_dir_run="/home/chrisr/sym/packages"
rpm_sources="/home/chrisr/SOURCES"
rpm_build="/home/chrisr/BUILD"
filename=""
ext=""
source_url=""

latest_tomcat="http://www.poolsaboveground.com/apache/tomcat/tomcat-8/v8.0.8/bin/apache-tomcat-8.0.8.tar.gz"
latest_glassfish="http://download.java.net/glassfish/4.0/release/glassfish-4.0.zip"
latest_activemq="http://www.apache.org/dyn/closer.cgi?path=/activemq/5.10.0/apache-activemq-5.10.0-bin.tar.gz"
latest_jetty="http://ftp-stud.fht-esslingen.de/pub/Mirrors/eclipse/jetty/stable-9/dist/jetty-distribution-9.2.1.v20140609.tar.gz"

echo
echo "-> Analyzing rpm spec file"
if [[ -f $spec_file_settings ]] ; then
    source create_rpm_spec.settings
fi

APP_NAME=DAM-$APP_NAME
install_dir=$FILES

# check for required information that will be inserted into the rpm spec file
if [[ -z $APP_NAME || -z $APP_SUMMARY || -z $FILES || -z $APP_GROUP || -z $APP_LICENSE || -z $APP_URL || -z $APP_DESCRIPTION ]] ; then
    echo "Error: Settings file does not contain enough package information."
    echo "See this page for more information: link to confluence."
    echo
    exit 1
fi

echo "-> Checking environment"
user=$(whoami)
if [[ $user != "chrisr" ]] ; then
    echo "Error: You need to run this script as chrisr."
    echo
    exit 1
fi

if ! [[ -z $source_url ]] ; then
    source_url_by_user=1
fi

# If the user does not specify the download path
# use default download paths to each application
# which is the latest version of the software
#
# Note that each vendor often has a different release naming scheme
# in addition to not always using the same urls for a previous version which makes
# it difficult to read version information from a file and fetch the given version
# Giving a source_url should be easier and fairly simple anyway
if [[ $source_url_by_user == 0 ]] ; then
    echo "-> User did not supply download path, constructing source_url based on latest version of $APP_NAME"
    if [[ $app == "tomcat" ]] ; then
        source_url="$latest_tomcat"
        filename=$(basename $source_url)
    elif [[ $app == "glassfish" ]] ; then
        source_url="$latest_glassfish"
        filename=$(basename $source_url)
    elif [[ $app == "jetty" ]] ; then
        source_url="$latest_jetty"
        filename=$(basename $source_url)
    elif [[ $app == "activemq" ]] ; then
        source_url="$latest_activemq"
        filename=$(basename $source_url)
    else
        echo "Error: No arguments or unspported application given as argument."
        echo
        exit 1
    fi
fi

# check filetype
filename=$(basename $source_url)
if [[ $filename =~ ".tar.gz" ]] ; then
    unpack="/bin/tar -xzf"
    ext="tar.gz"
elif [[ $filename =~ ".zip" ]] ; then
    unpack="/usr/bin/unzip -q"
    ext=".zip"
elif [[ $filename =~ ".gz" ]] ; then
    unpack="/bin/gunzip"
    ext=".gz"
else
    echo "Error: Unknown file extension for $filename used in $source_url."
    echo "Supported file types are: tar.gz, .zip, .gz and .tar."
    echo
    exit 1
fi

# we want the directory to be /opt/<app>/<version> and not /opt/<app>/<app>-<version>
echo "-> Creating rpm spec"
dir_ext_stripped_dot=$(basename $filename $ext)
dir_ext_stripped=$(echo $dir_ext_stripped_dot | sed 's/\.$//gi')
dir_removed_end_chars=${dir_ext_stripped%-*}
unpack_dir=$(ls $rpm_build)
dir_version_stripped=$(echo $dir_ext_stripped | sed 's/[a-zA-Z]//gi' | sed 's/-//gi')
unpack_dir_version_only=$dir_version_stripped

# Create the rpm spec file
{
cat <<-RPM_SPEC
Name: $APP_NAME
Version: $APP_VERSION
Release: 1%{?dist}
Summary: $APP_SUMMARY
Source0: $source_url
Group: $APP_GROUP
License: $APP_LICENSE
URL: $APP_URL
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXX)

%description
$APP_SUMMARY

%prep
rm -rf $rpm_sources/*
rm -rf $rpm_build/*
if [[ $source_url_by_user ]] ; then
    if ! [[ -f "$rpm_sources/$filename" ]] ; then
        wget -q $source_url -O $rpm_sources/$filename
    fi
else
    if ! [[ -f "$rpm_sources/$filename" ]] ; then
        wget -q $source_url -O $rpm_sources/$filename
    fi
fi

if [[ -s "$rpm_sources/$filename" ]] ; then
    $unpack $rpm_sources/$filename
else
    echo "Error: File size of downloaded file is zero in length, the specified version is probably not available for download."
    echo "Make sure the specified version is available for download at the vendors official site."
    echo
    exit 1
fi

%build
# empty, we dont build anything when we are dealing with binary files

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}$install_dir
if ! cp -a * %{buildroot}$install_dir ; then
    echo "Error: Failed to copy files from $(pwd) to %{buildroot}$install_dir."
    exit 1
fi

if ! mv %{buildroot}$install_dir/$unpack_dir %{buildroot}$install_dir/$unpack_dir_version_only ; then
    echo "Error: Unable to rename %{buildroot}$install_dir/$unpack_dir to %{buildroot}$install_dir/$unpack_dir_version_only."
    exit 1
fi
%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
$FILES

RPM_SPEC
} > $home_dir_run/$APP_NAME.spec

echo "-> RPM spec file created"
echo
echo "=========================================================="
echo "Building rpm for $APP_NAME version $APP_VERSION"
echo "=========================================================="
echo
if $build_package $home_dir_run/$APP_NAME.spec ; then
	echo
	echo "====================================================="
	echo "Successfully built RPM for $APP_NAME $APP_VERSION"
	echo "====================================================="
else
	echo "Error: Unable to create the RPM package."
fi

