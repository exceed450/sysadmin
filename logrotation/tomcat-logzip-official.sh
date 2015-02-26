#!/bin/bash
# @author chrisr
#
# Official tomcat logrotation script
# This script is compatible with log4j

# No files already in use will be compressed or moved so we can have a basic regular expression
tomcat_logfiles="[a-zA-Z0-9]+"
logfile=/tmp/tomcat-logrotation.log
fuser=/sbin/fuser
os=$(uname -s)
cronjob="5 0 * * * /etc/DAM/cron-run/daily/root/tomcat-logzip-official.sh -d $1 > /dev/null 2>&1"

if [[ $os == "Linux" ]] ; then
    linux=true
else
    linux=false
fi

if test -f /local/gnu/bin/mkdir ; then
    mkdir=/local/gnu/bin/mkdir
else
    mkdir=/bin/mkdir
fi

if ! [[ -f $fuser ]] ; then
   exit 1
fi

# dont output anything to the terminal unless you are attached to a terminal running it manually
if tty -s ; then
    :
else
    exec > /dev/null
fi

# add archive deletion to the cronjob
add_archive_deletion() {
    if [[ ! -z $1 ]] ; then
        if ! crontab -l > /tmp/temp_crontab ; then
            echo "Error: Unable to output cronjobs to file."
        fi
        
        IFS=$IFS_BACKUP
        check_cronjob=$(cat /tmp/temp_crontab)
        
        if [[ $check_cronjob =~ "tomcat-logzip-official" ]] ; then
            echo "Info: Cronjob already added."
            exit 1
        fi
        
        echo $cronjob >> /tmp/temp_crontab
        if crontab /tmp/temp_crontab ; then
            echo "Info: Cronjob was added successfully."
            echo "The follow job was added:"
            echo $cronjob
            echo
        else
            echo "Error: There was an error adding the cronjob."
            exit 1
        fi
        exit 0
    else
        echo "Error: -a option requires an argument."
        exit 1
    fi
}

# verify valid argument for -d option
# FIXME: Add a more general approach to handling arguments
set_archive_deletion() {
    if [[ ! -z $1 ]] ; then
        archive_deletion_int=$1
    else
        echo "Error: -d option requires an argument."
        exit 1
    fi
}

# remove logs older than 30 days (or older than the user specified number of days)
# in the archive directories
remove_old_logs() {
    # Handle spaces in the filename properly
    IFS_BACKUP=$IFS
    IFS=$(echo -ne "\n\b")
    
    for file in `find $1 -type f -mtime +$archive_deletion_int` ; do
        rm -fv $file >> $logfile
    done
}

# Not necessary to implement getopts at this time
if [[ ! -z $1 ]] ; then
    case "$1" in
        -d|--archive-deletion-int) shift ; set_archive_deletion $1 ;;
        -a|--add-archive-deletion) shift ; archive_deletion_int=$1 ; add_archive_deletion $archive_deletion_int ;;
        *) echo "Error: Invalid argument." ; exit 1 ;;
    esac
fi

echo "running at `date`" >> $logfile

for instance in `ls /var/log/tomcat`
do
    tomcat_logdir=/var/log/tomcat/$instance
    echo "--> archiving logs for $instance ..." >> $logfile

    for file in `find $tomcat_logdir -maxdepth 1 -type f`
    do
        year=$(stat -c "%y" $file | awk '{ print $1 }' | cut -f1 -d "-")
        month=$(stat -c "%y" $file | awk '{ print $1 }' | cut -f2 -d "-")
        day=$(stat -c "%y" $file | awk '{ print $1 }' | cut -f3 -d "-")
        tomcat_archive_dir="$tomcat_logdir/archive/$year/$month/$day"
        echo "Using $tomcat_archive_dir as tomcat archive log directory" >> $logfile
        
        if [[ $file =~ $regex_pattern || $file =~ $regex_pattern ]] ; then
            if [[ ! -d $tomcat_archive_dir ]] ; then
                echo "$tomcat_archive_dir does not exist, creating ..." >> $logfile
                $mkdir -pv $tomcat_archive_dir >> $logfile 
            fi

            if [[ ! -w $tomcat_archive_dir || ! -r $tomcat_archive_dir ]] ; then
                echo "$archive_log was not writeable or readable, aborting." >> $logfile
                exit 1
            fi
            
            if [[ $file =~ \.gz$ ]] ; then
                if ! mv $file $tomcat_archive_dir ; then
                    echo "Warning: Could NOT move already compressed file to $archive_log, continuing with next file." >> $logfile
                    continue
                fi
                echo "Info: Moved already compressed file $file to $tomcat_archive_dir." >> $logfile
                continue
            fi
            
            if $fuser -s $file ; then
                echo "file $file is already in use by an application, skipping compression of this file." >> $logfile
                continue
            fi
            
            echo "compressing logfile $file ..." >> $logfile
            if ! gzip -q $file ; then
                echo "Warning: Failed to compress $file, continuing with next file ..." >> $logfile
                continue
            else
                echo "Info: compressed file $file" >> $logfile
            fi

            # we'd also like to check the integrity after compression
            if ! gzip -q -t $file ; then
                echo "Warning: the integrity of $file was found to be inconsistent/corrupt, continuing with next file" >> $logfile
                continue
            fi
            
            if mv $file.gz $tomcat_archive_dir ; then
                echo "successfully moved the compressed file into the archive directory." >> $logfile
            else
                echo "Warning: could NOT move compressed file to archive directory." >> $logfile
            fi
        fi
        echo >> $logfile
    done
    if [[ ! -z $archive_deletion_int ]] ; then
        remove_old_logs $tomcat_logdir
    else
        echo "Info: Will not delete archive logs, -d option is not used." >> $logfile
    fi
    echo >> $logfile
done

echo "Completed logrotation successfully @ `date`" >> $logfile
echo >> $logfile
