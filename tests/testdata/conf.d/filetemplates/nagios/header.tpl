# confid:%(confid)s


############
# COMMANDS #
############

define command{
	command_name    host-notify-bus
	command_line    /usr/bin/printf "%%b" "event|$TIMET$|$HOSTNAME$|Host|$HOSTSTATE$|$HOSTOUTPUT$\\n" | socat -u - UNIX-CONNECT:%(socket)s
}
define command{
	command_name    service-notify-bus
	command_line    /usr/bin/printf "%%b" "event|$TIMET$|$HOSTNAME$|$SERVICEDESC$|$SERVICESTATE$|$SERVICEOUTPUT$\\n" | socat -u - UNIX-CONNECT:%(socket)s
}
define command{
	command_name	check_http_ars
	command_line	$USER1$/check_http -H $HOSTADDRESS$ -u /arsys/shared/login.jsp 
}
define command{
        command_name    check_dhcp_sudo
        command_line    /usr/bin/sudo $USER1$/check_dhcp -s $HOSTADDRESS$
}
define command {
        command_name    check_nrpe_rerouted
        command_line    $USER1$/check_nrpe -H $ARG1$ -c $ARG2$ -a $ARG3$
}
define command {
        command_name    check_nrpe_nossl
        command_line    $USER1$/check_nrpe -H $HOSTADDRESS$ -n -c $ARG1$ -a $ARG2$
}
define command {
        command_name    check_nrpe_1arg_nossl
        command_line    $USER1$/check_nrpe -H $HOSTADDRESS$ -n -c $ARG1$
}
define command {
	command_name        check_nrpe_1arg_timeout
	command_line        $USER1$/check_nrpe -t 15 -H $HOSTADDRESS$ -c $ARG1$
}
define command{
        command_name    check_proxy_noauth
        command_line    $USER1$/check_http -H $ARG2$ -I $HOSTADDRESS$ -p $ARG1$ -u http://$ARG2$
}
define command{
        command_name    check_proxy_auth
        command_line    $USER1$/check_http -H $ARG2$ -I $HOSTADDRESS$ -p $ARG1$ -u http://$ARG2$ -k "Proxy-Authorization: Basic login:passbase64encoded"
}
define command{
        command_name    my_check_radius
        command_line    $USER1$/check_radius -H $HOSTADDRESS$ -t 15 -P 1812 -F /etc/radiusclient/radiusclient.conf -u $ARG1$ -p $ARG2$
}
define command{
        command_name    process-service-perfdata
        command_line    $USER1$/perf2store -p /etc/vigilo/vigiconf/prod/perfdata/ -H '$HOSTNAME$' -s '$SERVICEDESC$' -a '$SERVICESTATE$' -t '$LASTSERVICECHECK$' -v '$SERVICEPERFDATA$'
}
define command{
        command_name    process-host-perfdata
        command_line    $USER1$/perf2store -p /etc/vigilo/vigiconf/prod/perfdata/ -H '$HOSTNAME$' -s 'HOST' -a '$HOSTSTATE$' -t '$LASTHOSTCHECK$' -v '$HOSTPERFDATA$'
}
define command{
	command_name            Collector
	command_line            $USER1$/Collector -H '$HOSTNAME$' 
}
define command{
	command_name            check_dummy
	command_line            $USER1$/check_dummy 0
}
define command{
	command_name            check_ldap_v3
	command_line            $USER1$/check_ldap -H $HOSTADDRESS$ -3 -b $ARG1$
}
define command{
        command_name            check_sysUpTime_v2
#        command_line            $USER1$/check_snmp -P 2c -H $HOSTADDRESS$ -C $ARG1$ -c $ARG2$: -w $ARG3$: -o iso.3.6.1.2.1.1.3.0
        command_line            $USER1$/check_sysuptime -v2 -C $ARG1$ -H $HOSTADDRESS$ -W $ARG3$ -T $ARG2$
}
define command{
        command_name            check_sysUpTime_v3
#        command_line            $USER1$/check_snmp -P 3 -H $HOSTADDRESS$ -c $ARG1$: -w $ARG2$: -o iso.3.6.1.2.1.1.3.0 -L authNoPriv -U $ARG3$ -a MD5 -A $ARG4$
        command_line            $USER1$/check_sysuptime -v3 -U $ARG3$ -A $ARG4$  -a MD5  -L authNoPriv -H $HOSTADDRESS$ -W $ARG2$ -T $ARG1$
}


############
# CONTACTS #
############

define contact{
	contact_name                    bus
	alias                           Message Bus
	service_notification_period     24x7
	host_notification_period        24x7
	service_notification_options    w,u,c,r
	host_notification_options       d,r
	service_notification_commands   service-notify-bus
	host_notification_commands      host-notify-bus
	email                           root@localhost
}


##################
# CONTACT GROUPS #
##################

define contactgroup{
    contactgroup_name       bots
    alias                   Nagios Notification robots
    members                 bus
}


################
# TIME PERIODS #
################

define timeperiod{
        timeperiod_name 24x7
        alias           24 Hours A Day, 7 Days A Week
        sunday          00:00-24:00
        monday          00:00-24:00
        tuesday         00:00-24:00
        wednesday       00:00-24:00
        thursday        00:00-24:00
        friday          00:00-24:00
        saturday        00:00-24:00
}
define timeperiod{
        timeperiod_name workhours
        alias           Standard Work Hours
        monday          09:00-17:00
        tuesday         09:00-17:00
        wednesday       09:00-17:00
        thursday        09:00-17:00
        friday          09:00-17:00
}
define timeperiod{
        timeperiod_name nonworkhours
        alias           Non-Work Hours
        sunday          00:00-24:00
        monday          00:00-09:00,17:00-24:00
        tuesday         00:00-09:00,17:00-24:00
        wednesday       00:00-09:00,17:00-24:00
        thursday        00:00-09:00,17:00-24:00
        friday          00:00-09:00,17:00-24:00
        saturday        00:00-24:00
}


#############
# TEMPLATES #
#############

define host{
	name                            generic-active-host
	active_checks_enabled           1
	passive_checks_enabled          0
	notifications_enabled           1       ; Host notifications are enabled
	event_handler_enabled           0       ; Host event handler is enabled
	flap_detection_enabled          1       ; Flap detection is enabled
	failure_prediction_enabled      1       ; Failure prediction is enabled
	process_perf_data               0       ; Process performance data
	retain_status_information       1       ; Retain status information across program restarts
	retain_nonstatus_information    1       ; Retain non-status information across program restarts
	max_check_attempts              1
	notification_interval           0
	notification_period             24x7
	notification_options            u,d,r,f
	contact_groups                  bots
	check_command                   check-host-alive
	register                        0       ; DONT REGISTER THIS DEFINITION - ITS NOT A REAL HOST, JUST A TEMPLATE!
}
define host{
	use                             generic-active-host
	name                            generic-passive-host
	passive_checks_enabled          1
	active_checks_enabled           0
	register                        0
}       
define service{
	name                            generic-active-service ; The 'name' of this service template
	active_checks_enabled           1       ; Active service checks are enabled
	passive_checks_enabled          0       ; Passive service checks are not accepted
	parallelize_check               1       ; Active service checks should be parallelized (disabling this can lead to major performance problems)
	obsess_over_service             1       ; We should obsess over this service (if necessary)
	check_freshness                 0       ; Default is to NOT check service 'freshness'
	notifications_enabled           1       ; Service notifications are enabled
	event_handler_enabled           1       ; Service event handler is enabled
	flap_detection_enabled          1       ; Flap detection is enabled
	failure_prediction_enabled      1       ; Failure prediction is enabled
	process_perf_data               0       ; Process performance data
	retain_status_information       1       ; Retain status information across program restarts
	retain_nonstatus_information    1       ; Retain non-status information across program restarts
	is_volatile                     0
	check_period                    24x7
	max_check_attempts              1
	normal_check_interval           5 
	retry_check_interval            1
	contact_groups                  bots
	notification_options            w,u,c,r,f
	notification_interval           0
	notification_period             24x7
	register                        0       ; DONT REGISTER THIS DEFINITION - ITS NOT A REAL SERVICE, JUST A TEMPLATE!
}
define service {
	use                             generic-active-service
	name                            generic-passive-service
	check_command                   check_dummy
	passive_checks_enabled          1       ; Passive service checks are enabled/accepted
	active_checks_enabled           0       ; Active service checks are enabled
	register                        0
	notification_options            w,c,r,f
}

