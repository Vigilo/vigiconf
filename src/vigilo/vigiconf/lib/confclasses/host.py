# -*- coding: utf-8 -*-
################################################################################
#
# Copyright (C) 2007-2009 CS-SI
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
################################################################################

"""
This module contains the Host class
"""

from __future__ import absolute_import

import os
import subprocess
import inspect
from xml.etree import ElementTree as ET # Python 2.5

#from vigilo.common.conf import settings
from vigilo.common.logging import get_logger
LOGGER = get_logger(__name__)

from vigilo.common.gettext import translate
_ = translate(__name__)

from . import get_text, get_attrib, parse_path
from .graph import Graph
from vigilo.vigiconf.lib import ParsingError, VigiConfError
from vigilo.vigiconf.lib import SNMP_ENTERPRISE_OID

from vigilo.models.session import DBSession
from vigilo.models.tables import SupItemGroup

class Host(object):
    """
    The Host configuration class.

    This class defines all the attributes and the methods of hosts in the
    configuration system.

    The attributes are added to the hosts hashmap, and the methods
    directly modify this hashmap.

    The methods are used by the tests definitions.

    @ivar hosts: the main hosts configuration dictionary
    @type hosts: C{dict}
    @ivar name: the hostname
    @type name: C{str}
    @ivar classes: the host classes
    @type classes: C{list} of C{str}
    """

    def __init__(self, hosts, filename, name, address, servergroup):
        self.hosts = hosts
        self.name = name
        self.classes = [ "all" ]
        self.hosts[name] = {
                "filename": unicode(filename),
                "name": name,
                "address": address,
                "serverGroup": servergroup,
                "otherGroups": set(),
                "services"       : {},
                "dataSources"    : {},
                "PDHandlers"     : {},
                "SNMPJobs"       : {},
                "telnetJobs"     : {},
                "metro_services" : {},
                "graphItems"     : {},
                "routeItems"     : {},
                "trapItems"      : {},
                "snmpTrap"       : {},
                "netflow"        : {},
                "graphGroups"    : {},
                "reports"        : {},
                "cti"            : 1,
                "hostTPL"        : "generic-active-host",
                "checkHostCMD"   : "check-host-alive",
                "snmpVersion"    : "2",
                "community"      : "public",
                "snmpPort"       : 161,
                "snmpOIDsPerPDU" : 10,
                "nagiosDirectives": {},
                "nagiosSrvDirs"  : {},
                "weight"         : 1,
            }
        self.attr_types = {"snmpPort": int,
                           "snmpOIDsPerPDU": int,
                           "weight": int,
                          }

    def get_attribute(self, attribute, default=False):
        """
        A very simple wrapper to get an attribute from the
        host's entry in the hashmap.
        @param attribute: the attribute to get
        @param default: default value if the attribute is not found
        """
        if self.hosts[self.name].has_key(attribute):
            return self.hosts[self.name][attribute]
        else:
            return default

    def set_attribute(self, attribute, value):
        """
        A very simple wrapper to set an attribute in the
        host's entry in the hashmap.
        @param attribute: the attribute to set
        @param value: the value to set the attribute to
        """
        if attribute in self.attr_types \
                and not isinstance(value, self.attr_types[attribute]):
            value = self.attr_types[attribute](value)
        self.hosts[self.name][attribute] = value

    def update_attributes(self, attributes):
        """
        A very simple wrapper to set many attributes at once in the host's
        entry in the hashmap.

        @param attributes: the attributes to set
        @type  attributes: C{dict}
        """
        self.hosts[self.name].update(attributes)

    def add_tests(self, test_list, args={}, weight=None, directives=None):
        """
        Add a list of tests to this host, with the provided arguments

        @param test_list: the list of tests
        @type  test_list: C{list} of C{Test<.test.Test>}
        @param args: the test arguments
        @type  args: C{dict}
        @param weight: the test weight
        @type  weight: C{int}
        """
        if weight is None:
            weight = 1
        if directives is None:
            directives = {}
        for test_class in test_list:
            inst = test_class()
            try:
                inst.directives = directives
                inst.weight = weight
                inst.add_test(self, **args)
            except TypeError:
                spec = inspect.getargspec(inst.add_test)
                # On récupère la liste des arguments obligatoires.
                defaults = spec[3]
                if defaults is None:
                    args = spec[0][2:]
                else:
                    args = spec[0][2:-len(defaults)]
                message = _('Test "%(test_name)s" on "%(host)s" needs the '
                            'following arguments: %(args)s (and only those)') \
                          % {'test_name': str(test_class.__name__),
                             'host': self.name,
                             'args': ', '.join(args),
                            }
                raise VigiConfError(message)

#    def apply_template(self, tpl):
#        """
#        Apply a host template to this host
#        @param tpl: the template name
#        @type  tpl: C{str}
#        """
#        conf.hosttemplatefactory.apply(self, tpl)


#### Access the global dicts ####

    def add_group(self, group_name):
        """
        Add the host to a new secondary group
        @param group_name: the group to be added to
        @type  group_name: C{str}
        """
        group_name = unicode(group_name)
        self.hosts[self.name]['otherGroups'].add(group_name)

    def add_dependency(self, service="Host", deps=None, options=None, cti=1):
        """
        Add a topological dependency, from "origin" to "target".

        @param service: the origin service. If the value is the string "Host",
            then the host itself is the origin.
        @type  service: C{str}
        @param deps: the target dependencies. If deps is a C{str}, then it is
            considered as a hostname. If deps is a C{dict}, then it may be of the
            following form::
                {
                    "and": [(host1, "Host"), (host2, "Service1")]
                    "or": [(host3, "Host")]
                }
        @type  deps: C{str} or C{dict}
        @param options: TODO:
        @type  options: C{list}
        @param cti: alert reference (Category - Type - Item)
        @type  cti: C{int}
        @todo: finish agument description
        @todo: deprecated (database management)
        """
        if deps is None:
            return
        if options is None:
            options = []
        if isinstance(deps, str) and deps != "":
            # target argument given as string
            deps = { "and": [(deps, "Host")] }
        import vigilo.vigiconf.conf as conf
        conf.dependencies[(self.name, service)] = {"deps": {"and": [],
                                                            "or": []},
                                                   "options": options,
                                                   'cti': cti}
        for dep_type, dep_list in deps.iteritems():
            for dep in dep_list:
                if isinstance(dep, str):
                    dep = (dep, "Host")
                conf.dependencies[(self.name, service)]["deps"]\
                                                       [dep_type].append(dep)

#### Access the hosts dict ####

    def get(self, prop):
        """
        A generic function to get a property from the main hashmap
        @param prop: the property to get
        @type  prop: hashable
        """
        return self.hosts[self.name][prop]

    def add(self, hostname, prop, key, value):
        """
        A generic function to add a key/value to a property
        @param hostname: the hostname to add to. Usually L{name}.
        @type  hostname: C{str}
        @param prop: the property to add to
        @type  prop: hashable
        @param key: the key to add to the property
        @type  key: hashable
        @param value: the value to add to the property
        @type  value: anything
        """
        if not self.hosts[hostname].has_key(prop):
            self.hosts[hostname][prop] = {}
        self.hosts[hostname][prop].update({key: value})

    def add_sub(self, hostname, prop, subprop, key, value):
        """
        A generic function to add a key/value to a subproperty
        @param hostname: the hostname to add to. Usually L{name}.
        @type  hostname: C{str}
        @param prop: the property to add to
        @type  prop: hashable
        @param subprop: the subproperty to add to
        @type  subprop: hashable
        @param key: the key to add to the property
        @type  key: hashable
        @param value: the value to add to the property
        @type  value: anything
        """
        if not self.hosts[hostname].has_key(prop):
            self.hosts[hostname][prop] = {}
        if not self.hosts[hostname][prop].has_key(subprop):
            self.hosts[hostname][prop][subprop] = {}
        self.hosts[hostname][prop][subprop].update({key: value})

    def add_trap(self, service, oid, data={}):
        """
        Add a SNMPT Trap handler (for snmptt)
        @param service: the service description (nagios service)
        @type service: C{str}
        @param oid: as name. For identify snmp trap.
        @type oid: C{str}
        @param data: the dictionnary contains :
            path to script to execute C{str},
            label: snmp trap event name C{str}
            address: ip address to match in snmptt C{str}
            service: service description (nagios service) C{str} (to remove?)
        @type data: C{dict}
        """
        if not self.hosts[self.name].has_key("snmpTrap"):
            self.hosts[self.name]["snmpTrap"] = {}
        if not self.hosts[self.name]["snmpTrap"].has_key(service):
            self.hosts[self.name]["snmpTrap"][service] = {}
        self.hosts[self.name]["snmpTrap"][service][oid] = {}

        if not "address" in data.keys():
            data["address"] = self.hosts[self.name]["address"]
        for key, value in data.iteritems():
            self.hosts[self.name]["snmpTrap"][service][oid].update({key: value})

    def add_netflow(self, data={}):
        """
        Add netflow handler (for pmacct and pmacct-snmp)
        @param data: dictionary contains data like inbound, outboun, binary
        path and ip list.
        @type data: C{dict}
        """
        if not self.hosts[self.name].has_key("netflow"):
            self.hosts[self.name]["netflow"] = {}
        self.hosts[self.name]["netflow"] = data.copy()

#### Collector-related functions ####

    def add_collector_service(self, label, function, params, variables, cti=1,
                                    reroutefor=None, weight=1,
                                    directives=None):
        """
        Add a supervision service to the Collector
        @param label: the service display label
        @type  label: C{str}
        @param function: the Collector function to use
        @type  function: C{str}
        @param params: the parameters for the Collector function
        @type  params: C{list}
        @param variables: the variables for the Collector function
        @type  variables: C{list}
        @param cti: alert reference (Category - Type - Item)
        @type  cti: C{int}
        @param reroutefor: Service routing information.
            This parameter indicates that the given service receives
            information for another service, whose host and label are
            given by the "host" and "service" keys of this dict,
            respectively.
        @type  reroutefor: C{dict}
        @param weight: service weight
        @type  weight: C{int}
        """
        # Handle rerouting
        if reroutefor == None:
            target = self.name
            service = label
            reroutedby = None
        else:
            target = reroutefor["host"]
            service = reroutefor['service']
            reroutedby = {
                'host': self.name,
                'service': label,
            }

        if directives is None:
            directives = {}
        for (dname, dvalue) in directives.iteritems():
            self.add_sub(target, "nagiosSrvDirs", service, dname, str(dvalue))

        # Add the Nagios service (rerouting-dependant)
        self.add(target, "services", service, {'type': 'passive',
                                               'cti': cti,
                                               "weight": weight,
                                               "directives": directives,
                                               "reRoutedBy": reroutedby,
                                              })
        # Add the Collector service (rerouting is handled inside the Collector)
        self.add(self.name, "SNMPJobs", (label, 'service'),
                                        {'function': function,
                                         'params': params,
                                         'vars': variables,
                                         'reRouteFor': reroutefor,
                                         } )

    def add_collector_metro(self, name, function, params, variables, dstype,
                                  label=None, reroutefor=None):
        """
        Add a metrology datasource to the Collector
        @param name: the datasource name
        @type  name: C{str}
        @param function: the Collector function to use
        @type  function: C{str}
        @param params: the parameters for the Collector function
        @type  params: C{list}
        @param variables: the variables for the Collector function
        @type  variables: C{list}
        @param dstype: datasource type
        @type  dstype: "GAUGE" or "COUNTER", see RRDtool documentation
        @param label: the datasource display label
        @type  label: C{str}
        @param reroutefor: service routing information
        @type  reroutefor: C{dict} with "host" and "service" as keys
        """
        if not label:
            label = name
        # Handle rerouting
        if reroutefor is None:
            target = self.name
            service = name
        else:
            target = reroutefor['host']
            service = reroutefor['service']

        # Add the RRD datasource (rerouting-dependant)
        self.add(target, "dataSources", service, {
            'dsType': dstype,
            'label': label,
        })
        # Add the Collector service (rerouting is handled inside the Collector)
        self.add(self.name, "SNMPJobs", (name, 'perfData'),
                                        {'function': function,
                                         'params': params,
                                         'vars': variables,
                                         'reRouteFor': reroutefor,
                                         } )

    def add_collector_service_and_metro(self, name, label, supfunction,
                    supparams, supvars, metrofunction, metroparams, metrovars,
                    dstype, cti=1, reroutefor=None, weight=1,
                    directives=None):
        """
        Helper function for L{add_collector_service}() and
        L{add_collector_metro}().
        @param name: the service and datasource name
        @type  name: C{str}
        @param label: the service and datasource display label
        @type  label: C{str}
        @param supfunction: the Collector function to use for supervision
        @type  supfunction: C{str}
        @param supparams: the parameters for the Collector supervision function
        @type  supparams: C{list}
        @param supvars: the variables for the Collector supervision function
        @type  supvars: C{list}
        @param metrofunction: the Collector function to use for metrology
        @type  metrofunction: C{str}
        @param metroparams: the parameters for the Collector metrology function
        @type  metroparams: C{list}
        @param metrovars: the variables for the Collector metrology function
        @type  metrovars: C{list}
        @param dstype: datasource type
        @type  dstype: "GAUGE" or "COUNTER", see RRDtool documentation
        @param cti: alert reference (Category - Type - Item)
        @type  cti: C{int}
        @param reroutefor: service routing information
        @type  reroutefor: C{dict} with "host" and "service" as keys
        @param weight: service weight
        @type  weight: C{int}
        """
        self.add_collector_service(name, supfunction, supparams, supvars,
                        cti=cti, reroutefor=reroutefor, weight=weight,
                        directives=directives)
        self.add_collector_metro(name, metrofunction, metroparams, metrovars,
                                 dstype, label=label, reroutefor=reroutefor)

    def add_collector_service_and_metro_and_graph(self, name, label, oid,
            th1, th2, dstype, template, vlabel, supcaption=None,
            supfunction="thresholds_OID_simple", metrofunction="directValue",
            group="General", cti=1, reroutefor=None, weight=1, directives=None):
        """
        Helper function for L{add_collector_service}(),
        L{add_collector_metro}() and L{add_graph}(). See those methods for
        argument details
        """
        if not label:
            label = name
        if supcaption is None:
            supcaption = "%s: %%s" % label
        self.add_collector_service_and_metro(name, label, supfunction,
                    [th1, th2, supcaption], ["GET/%s"%oid], metrofunction,
                    [], [ "GET/%s"%oid ], dstype, cti=cti,
                    reroutefor=reroutefor, weight=weight, directives=directives)
        if reroutefor != None:
            target = reroutefor['host']
            name = reroutefor['service']
        else:
            target = self.name
        graph = Graph(self.hosts, unicode(label), [ unicode(name) ],
                      unicode(template), unicode(vlabel), group=unicode(group))
        graph.add_to_host(target)

    def add_graph(self, title, dslist, template, vlabel,
                        group="General", factors=None,
                        max_values=None, last_is_max=False):
        """
        Add a graph to the host
        @param title: The graph title
        @type  title: C{str}
        @param dslist: The list of datasources to include
        @type  dslist: C{list} of C{str}
        @param template: The name of the graph template
        @type  template: C{str}
        @param vlabel: The vertical label
        @type  vlabel: C{str}
        @param group: The group of the graph
        @type  group: C{str}
        @param factors: the factors to use, if any
        @type  factors: C{dict}
        @param max_values: the maximum values for each datasource, if any
        @type  max_values: C{dict}
        """
        graph = Graph(self.hosts, unicode(title), map(unicode, dslist),
                      unicode(template), unicode(vlabel),
                      group=unicode(group), factors=factors,
                      max_values=max_values, last_is_max=last_is_max)
        graph.add_to_host(self.name)

    def add_report(self, title, reportname, datesetting=0):
        """
        Add a Report to an host
        @deprecated: This function is not used anymore in Vigilo V2.
        @param title: Specify a title into SupNavigator
        @type  title: C{str}
        @param reportname: The name of the report with extension
        @type  reportname: C{str}
        @param datesetting: The number of days to report
        @type  datesetting: C{str}
        """
        if title is not None and title not in self.get("reports"):
            self.add(self.name, "reports", title, {"reportName": reportname,
                                                   "dateSetting": datesetting})

    def add_external_sup_service(self, name, command=None, cti=1,
                                weight=1, directives=None):
        """
        Add a standard Nagios service
        @param name: the service name
        @type  name: C{str}
        @param command: the command to use
        @type  command: C{str}
        @param cti: alert reference (Category - Type - Item)
        @type  cti: C{int}
        @param weight: service weight
        @type  weight: C{int}
        """
        if directives is None:
            directives = {}
        for (dname, dvalue) in directives.iteritems():
            self.add_nagios_service_directive(name, dname, dvalue)

        definition =  {'type': type,
                       'command': command,
                       'cti': cti,
                       'weight': weight,
                       'directives': directives,
                       'reRoutedBy': None,
                      }
        if command is None:
            definition["type"] = "passive"
        else:
            definition["type"] = "active"
            definition["command"] = command
        self.add(self.name, 'services', name, definition)

    def add_perfdata_handler(self, service, name, label, perfdatavarname,
                              dstype="GAUGE", reroutefor=None):
        """
        Add a perfdata handler: send the performance data from the nagios
        plugins to the RRDs
        @param service: the service name
        @type  service: C{str}
        @param name: the datasource name (rrd filename)
        @type  name: C{str}
        @param label: the datasource display label
        @type  label: C{str}
        @param perfdatavarname: the name of the perfdata indicator
        @type  perfdatavarname: C{str}
        @param dstype: datasource type
        @type  dstype: "GAUGE" or "COUNTER", see RRDtool documentation
        @param reroutefor: service routing information
        @type  reroutefor: C{dict} with "host" and "service" as keys
        """
        if reroutefor == None:
            target = self.name
        else:
            target = reroutefor['host']
        # Add the RRD
        self.add(target, "dataSources", name,
                 {'dsType': dstype, 'label': label})
        # Add the perfdata handler in Nagios
        if not self.get('PDHandlers').has_key(service):
            self.add(self.name, "PDHandlers", service, [])
        existing = [ pdh["perfDataVarName"] for pdh in
                     self.hosts[self.name]['PDHandlers'][service] ]
        if perfdatavarname not in existing:
            self.hosts[self.name]['PDHandlers'][service].append(
                    {'name': name, 'perfDataVarName': perfdatavarname,
                     'reRouteFor': reroutefor})

    def add_metro_service(self, servicename, metroname, warn, crit, factor=1, weight=1):
        """
        Add a Nagios test on the values stored in a RRD file
        @param servicename: the name of the Nagios service
        @type  servicename: C{str}
        @param metroname: the name of the metrology datasource
        @type  metroname: C{str}
        @param warn: the WARNING threshold.
        @type  warn: C{str}
        @param crit: the CRITICAL threshold.
        @type  crit: C{str}
        @param factor: the factor to use, if any
        @type  factor: C{int} or C{float}
        """
        oid = [".1.3.6.1.4.1", str(SNMP_ENTERPRISE_OID)]
        for char in self.name:
            oid.append(str(ord(char)))
        oid.append(str(ord("/")))
        for char in metroname:
            oid.append(str(ord(char)))
        # Ajout du service Nagios
        self.add(self.name, "services", servicename,
                 {'type': 'passive',
                  "weight": weight,
                  "directives": {},
                  "reRoutedBy": None,
                  })
        # Ajout du service Collector sur le serveur de métro
        self.add(self.name, "metro_services", (servicename, 'service'),
                 {'function': "simple_factor",
                  'params': [warn, crit, factor],
                  'vars': [ "GET/%s" % ".".join(oid) ],
                  'reRouteFor': None,
                  } )

    def add_tag(self, service, name, value):
        """
        Add a tag to a host or a service. This tag is associated with a value.
        @param service: the service to add the tag to. If it is the string
            "Host", then the tag is added to the host itself.
        @type  service: C{str}
        @param name: the tag name
        @type  name: C{str}
        @param value: the tag value
        @type  value: C{int}
        """
        if service is None or service.lower() == "host":
            target = self.hosts[self.name]
        else:
            target = self.hosts[self.name]["services"][service]
        if not target.has_key("tags"):
            target["tags"] = {}
        target["tags"][name] = value

    def add_nagios_directive(self, name, value):
        """ Add a generic nagios directive

            @param name: the directive name
            @type  name: C{str}
            @param value: the directive value
            @type  value: C{str}
        """
        self.add(self.name, "nagiosDirectives", name, str(value))

    def add_nagios_service_directive(self, service, name, value):
        """ Add a generic nagios directive for a service

            @param service: the service, ie 'Interface eth0'
            @type  service: C{str}
            @param name: the directive name
            @type  name: C{str}
            @param value: the directive value
            @type  value: C{str}
        """
        self.add_sub(self.name, "nagiosSrvDirs", service, name, str(value))


class HostFactory(object):
    """
    Factory to create Host objects
    """

    def __init__(self, hostsdir, hosttemplatefactory, testfactory):
        self.hosts = {}
        self.hosttemplatefactory = hosttemplatefactory
        self.testfactory = testfactory
        self.hostsdir = hostsdir

# VIGILO_EXIG_VIGILO_CONFIGURATION_0010 : Fonctions de préparation des
#   configurations de la supervision en mode CLI
#
#   configuration des hôtes à superviser : ajout/modification/suppression
#     d'un hôte ou d'une liste d'hôtes
#   configuration des paramètres d'authentification SNMP pour chaque hôte à
#     superviser ( version V1,V2c,V3) et adresse IP pour l'interface SNMP
#   configuration des services et seuils d'alarmes :
#     ajout/modification/suppression d'un service et positionnement des seuils
#     d'alarme Warning/Critical/OK
#   configuration des valeurs de performances à collecter :
#     ajout/modification/suppression d'une valeur de performance
#   configuration des cartes automatiques;
    def load(self, validation=True):
        """
        Load the defined hosts
        """
        for root, dirs, files in os.walk(self.hostsdir):
            for f in files:
                fullpath = os.path.join(root, f)
                if not f.endswith(".xml"):
                    continue
                if validation:
                    self._validatehost(fullpath)
                self._loadhosts(fullpath)
                LOGGER.debug("Successfully parsed %s", fullpath)
            for d in dirs: # Don't visit subversion/CVS directories
                if d.startswith("."):
                    dirs.remove(d)
                if d == "CVS":
                    dirs.remove("CVS")
        return self.hosts


    def _validatehost(self, source):
        """
        Validate the XML against the XSD using xmllint

        @note: this could take time.
        @todo: use lxml for python-based validation
        @param source: an XML file (or stream)
        @type  source: C{str} or C{file}
        """
        xsd = os.path.join(os.path.dirname(__file__), "..", "..",
                           "validation", "xsd", "host.xsd")
        devnull = open("/dev/null", "w")
        result = subprocess.call(["xmllint", "--noout", "--schema", xsd, source],
                    stdout=devnull, stderr=subprocess.STDOUT)
        devnull.close()
        # Lorsque le fichier est valide.
        if result == 0:
            return
        # Plus assez de mémoire.
        if result == 9:
            raise ParsingError(_("Not enough memory to validate %(file)s "
                                 "using schema %(schema)s") % {
                                    'schema': xsd,
                                    'file': source,
                                })
        # Schéma de validation ou DTD invalide.
        if result in (2, 5):
            raise ParsingError(_("Invalid XML validation schema %(schema)s "
                                "found while validating %(file)s") % {
                                    'schema': xsd,
                                    'file': source,
                                })
        # Erreur de validation du fichier par rapport au schéma.
        if result in (3, 4):
            raise ParsingError(_("XML validation failed (%(file)s with "
                                "schema %(schema)s)") % {
                                    'schema': xsd,
                                    'file': source,
                                })
        raise ParsingError(_("XML validation failed for file %(file)s, "
                            "using schema %(schema)s, due to an error. "
                            "Make sure the permissions are set correctly.") % {
                                'schema': xsd,
                                'file': source,
                            })

    def _loadhosts(self, source):
        """
        Load a Host from an XML file

        TODO: refactoring: implémenter un loader XML pour les hosts, comme pour
        les autres entités.

        @param source: an XML file (or stream)
        @type  source: C{str} or C{file}
        """
        test_name = None
        cur_host = None
        process_nagios = False
        test_directives = {}
        directives = {}
        tests = []
        weight = None

        for event, elem in ET.iterparse(source, events=("start", "end")):
            if event == "start":
                if elem.tag == "host":
                    test_name = None
                    directives = {}
                    tests = []
                    weight = None

                    name = get_attrib(elem, 'name')

                    address = get_attrib(elem, 'address')
                    if not address:
                        address = name

                    ventilation = get_attrib(elem, 'ventilation')

                    # Si le groupe indiqué est un chemin contenant
                    # plusieurs composantes, par exemple: "A/B".
                    # Alors il est invalide ici.
                    parts = parse_path(ventilation)

                    # NB: parts peut valoir None si le parsing a échoué.
                    if ventilation and (not parts or len(parts) > 1):
                        raise ParsingError(_("Invalid ventilation group: %s") %
                            ventilation)

                    # On génère le nom de fichier relatif par rapport
                    # à la racine du checkout SVN.
                    cur_host = Host(
                        self.hosts,
                        source,
                        name,
                        address,
                        ventilation
                    )
                    self.hosttemplatefactory.apply(cur_host, "default")

                elif elem.tag == "nagios":
                    process_nagios = True

                elif elem.tag == "test":
                    test_name = get_attrib(elem, "name")
                    test_directives = {}

            else: # Événement de type "end"
                if elem.tag == "template":
                    self.hosttemplatefactory.apply(cur_host, get_text(elem))

                elif elem.tag == "class":
                    cur_host.classes.append(get_text(elem))

                elif elem.tag == "test":
                    test_weight = get_attrib(elem, 'weight')
                    try:
                        test_weight = int(test_weight)
                    except ValueError:
                        raise ParsingError(
                            _("Invalid weight value for test %(test)s "
                                "on host %(host)s: %(weight)r") % {
                                'test': test_name,
                                'host': cur_host.name,
                                'weight': test_weight,
                            })
                    except TypeError:
                        pass # C'est None, on laisse prendre la valeur par défaut
                    args = {}
                    for arg in elem.getchildren():
                        if arg.tag == 'arg':
                            args[get_attrib(arg, 'name')] = get_text(arg)
                    tests.append((test_name, args, test_weight, test_directives))
                    test_name = None

                elif elem.tag == "attribute":
                    value = get_text(elem)
                    items = [get_text(i) for i in elem.getchildren()
                                     if i.tag == "item" ]
                    if items:
                        value = items
                    cur_host.set_attribute(get_attrib(elem, 'name'), value)

                elif elem.tag == "tag":
                    cur_host.add_tag(get_attrib(elem, 'service'),
                                     get_attrib(elem, 'name'),
                                     get_text(elem))

                elif elem.tag == "directive":
                    if not process_nagios: continue

                    dvalue = get_text(elem).strip()
                    dname = get_attrib(elem, 'name').strip()
                    if not dname:
                        continue

                    # directive nagios
                    if test_name is None:
                        directives[dname] = dvalue
                    else:
                        test_directives[dname] = dvalue

                elif elem.tag == "group":
                    group_name = get_text(elem)
                    if not parse_path(group_name):
                        raise ParsingError(_('Invalid group name (%s)')
                            % group_name)
                    cur_host.add_group(group_name)

                elif elem.tag == "weight":
                    host_weight = get_text(elem)
                    try:
                        weight = int(host_weight)
                    except ValueError:
                        raise ParsingError(_("Invalid weight value for "
                            "host %(host)s: %(weight)r") % {
                            'host': cur_host.name,
                            'weight': host_weight,
                        })
                    except TypeError:
                        pass # C'est None, on laisse prendre la valeur par défaut

                elif elem.tag == "nagios":
                    process_nagios = False

                elif elem.tag == "host":
                    if not len(cur_host.get_attribute('otherGroups')):
                        raise ParsingError(_('You must associate host "%s" with '
                            'at least one group.') % cur_host.name)

                    if weight is not None:
                        cur_host.set_attribute("weight", weight)

                    for test_params in tests:
                        test_list = self.testfactory.get_test(test_params[0], cur_host.classes)
                        cur_host.add_tests(test_list, *test_params[1:])

                    for (dname, dvalue) in directives.iteritems():
                        cur_host.add_nagios_directive(dname, dvalue)

                    LOGGER.debug("Loaded host %(host)s, address %(address)s" %
                                 {'host': cur_host.name,
                                  'address': cur_host.get_attribute('address'),
                                 })
                    elem.clear()
                    cur_host = None

# vim:set expandtab tabstop=4 shiftwidth=4:
