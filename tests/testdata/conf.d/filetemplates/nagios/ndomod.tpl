# confid:%(confid)s
#####################################################################
# NDOMOD CONFIG FILE
#
# Last Modified: 02-18-2007
#####################################################################


# INSTANCE NAME
# This option identifies the "name" associated with this particular
# instance of Nagios and is used to seperate data coming from multiple
# instances.  Defaults to 'default' (without quotes).

instance_name=%(name)s



# OUTPUT TYPE
# This option determines what type of output sink the NDO NEB module
# should use for data output.  Valid options include:
#   file       = standard text file
#   tcpsocket  = TCP socket
#   unixsocket = UNIX domain socket (default)

#output_type=file
output_type=tcpsocket
#output_type=unixsocket



# OUTPUT
# This option determines the name and path of the file or UNIX domain 
# socket to which output will be sent if the output type option specified
# above is "file" or "unixsocket", respectively.  If the output type
# option is "tcpsocket", this option is used to specify the IP address
# of fully qualified domain name of the host that the module should
# connect to for sending output.

#output=/usr/local/nagios/var/ndo.dat
output=%(nagvis_server)s
#output=/usr/local/nagios/var/ndo.sock
#output=/tmp/ndo.sock



# TCP PORT
# This option determines what port the module will connect to in
# order to send output.  This option is only vlaid if the output type
# option specified above is "tcpsocket".

tcp_port=5668



# OUTPUT BUFFER
# This option determines the size of the output buffer, which will help
# prevent data from getting lost if there is a temporary disconnect from
# the data sink.  The number of items specified here is the number of
# lines (each of variable size) of output that will be buffered.

output_buffer_items=5000



# BUFFER FILE
# This option is used to specify a file which will be used to store the
# contents of buffered data which could not be sent to the NDO2DB daemon
# before Nagios shuts down.  Prior to shutting down, the NDO NEB module
# will write all buffered data to this file for later processing.  When
# Nagios (re)starts, the NDO NEB module will read the contents of this
# file and send it to the NDO2DB daemon for processing.

#buffer_file=/usr/local/nagios/var/ndomod.tmp
buffer_file=/tmp/ndomod.tmp



# FILE ROTATION INTERVAL
# This option determines how often (in seconds) the output file is
# rotated by Nagios.  File rotation is handled by Nagios by executing
# the command defined by the file_rotation_command option.  This
# option has no effect if the output_type option is a socket.

file_rotation_interval=14400



# FILE ROTATION COMMAND
# This option specified the command (as defined in Nagios) that is
# used to rotate the output file at the interval specified by the
# file_rotation_interval option.  This option has no effect if the
# output_type option is a socket.
#
# See the file 'misccommands.cfg' for an example command definition
# that you can use to rotate the log file.

#file_rotation_command=rotate_ndo_log



# FILE ROTATION TIMEOUT
# This option specified the maximum number of seconds that the file
# rotation command should be allowed to run before being prematurely
# terminated.

file_rotation_timeout=60



# RECONNECT INTERVAL
# This option determines how often (in seconds) that the NDO NEB
# module will attempt to re-connect to the output file or socket if
# a connection to it is lost.

reconnect_interval=15



# RECONNECT WARNING INTERVAL
# This option determines how often (in seconds) a warning message will
# be logged to the Nagios log file if a connection to the output file
# or socket cannot be re-established.

reconnect_warning_interval=15
#reconnect_warning_interval=900



# DATA PROCESSING OPTION
# This option determines what data the NDO NEB module will process. 
# Do not mess with this option unless you know what you're doing!!!!
# Read the source code (include/ndbxtmod.h) to determine what values
# to use here.  Values from source code should be OR'ed to get the
# value to use here.  A value of -1 will cause all data to be processed.

data_processing_options=-1



# CONFIG OUTPUT OPTION
# This option determines what types of configuration data the NDO
# NEB module will dump from Nagios.  Values can be OR'ed together.
# Values: 
# 	  0 = Don't dump any configuration information
#         1 = Dump only original config (from config files)
#         2 = Dump config only after retained information has been restored
#         3 = Dump both original and retained configuration

config_output_options=2

