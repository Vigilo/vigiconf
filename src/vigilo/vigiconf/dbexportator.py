#!/usr/bin/env python
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
This module contains the DBExportator, a tool to export
hosts and services configuration into the vigilo database.
"""

from __future__ import absolute_import

import sys
import syslog

from vigilo.models.session import DBSession
from vigilo.models import Host, HostGroup, ServiceLowLevel, ServiceGroup
from vigilo.models import Graph, GraphGroup
from vigilo.models import Application, HostApplication

from . import conf

def update_apps_db():
    """ Update database with new apps
    TODO: add new hosts here to be able to ventilate before the db export ??
    """
    apps = conf.apps
    appsGroupsByServer = conf.appsGroupsByServer
    
    # apps
    for name in apps.keys():
        app = Application.by_app_name(name)
        if not app:
            app = Application(name=name)
            DBSession.add(app)
    
    DBSession.flush()

def export_conf_db():
    """
    Update database with hostConf data.
    @returns: None
    """
    hostsConf = conf.hostsConf
    hostsGroups = conf.hostsGroups
    groupsHierarchy = conf.groupsHierarchy
    
    # hosts groups
    try:
        for name, desc in hostsGroups.iteritems():
            hg = HostGroup.by_group_name(name)
            if not hg:
                hg = HostGroup(name=name)
            DBSession.add(hg)
    except:
        DBSession.rollback()
        raise
    
    # hosts
    try:
        for hostname, host in hostsConf.iteritems():
            h = Host.by_host_name(hostname)
            if h:
                # update host object
                h.checkhostcmd=host['checkHostCMD']
                h.hosttpl=host['hostTPL']
                h.snmpcommunity=host['community']
                h.snmpoidsperpdu = host['snmpOIDsPerPDU']
                h.snmpversion = host['snmpVersion']
                h.mainip=host['mainIP']
                h.snmpport=host['port']
            else:
                # create host object
                h = Host(name=hostname, checkhostcmd=host['checkHostCMD'],
                               hosttpl=host['hostTPL'], snmpcommunity=host['community'],
                               mainip=host['mainIP'], snmpport=host['port'],
                               snmpoidsperpdu=host['snmpOIDsPerPDU'], weight=1,
                               snmpversion=host['snmpVersion'])
                DBSession.add(h)
            # add groups to host
            h.groups = [HostGroup.by_group_name(host['serverGroup']),]
            for og in host['otherGroups']:
                h.groups.append(HostGroup.by_group_name(og))
            
            # export graphes groups
            export_host_graphgroups(host['graphGroups'], h)
            
            # export graphes
            export_host_graphitems(host['graphItems'], h)
            
    except:
        DBSession.rollback()
        raise
    
    # services
    try:
        for hostname, host in hostsConf.iteritems():
            for srvname, srv in host['services'].iteritems():
                s = ServiceLowLevel.by_host_service_name(hostname, srvname)
                if s:
                    s.command = srv['command']
                else:
                    # create service object
                    cmd = u'none'
                    if srv.has_key('command'):
                        cmd = srv['command']
                    s = ServiceLowLevel(servicename=srvname, op_dep=u'-',
                                        host=Host.by_host_name(hostname),
                                        command=cmd, weight=1)
                    DBSession.add(s)
    except:
        DBSession.rollback()
        raise
    
    # groups hierarchies
    for parent_name, children in groupsHierarchy.iteritems():
        parent = HostGroup.by_group_name(parent_name)
        parent.children = []
        for name in children:
            g = HostGroup.by_group_name(name)
            g.parent = parent
    
    DBSession.flush()

def export_host_graphgroups(graphgroups, h):
    """
    Update database with graph groups for a host.
    
    @param graphgroups: a dict describing the graph groups hierarchy for a host.
    @type graphgroups: C{dict}
    @param h: host
    @param h: C{Host}
    @returns: None
    """
    # reset hierarchy
    for graph in DBSession.query(Graph):
        graph.groups = []
        
    for groupname, graphnames in graphgroups.iteritems():
        group = GraphGroup.by_group_name(groupname)
        if group:
            group.children = [] # redundant with graph.groups = [] ?
        else:
            group = GraphGroup(name=groupname)
            DBSession.add(group)
        for name in graphnames:
            graph = DBSession.query(Graph).filter(Graph.name == name).first()
            if not graph:
                graph = Graph(name=name, template=u'lines', vlabel=u'unknown')
            graph.groups.append(group)
    
    DBSession.flush()
        


def export_host_graphitems(graphitems, h):
    """
    Update database with graph items for a host.
    
    @param graphitems: a dict describing the graph items for a host.
    @type graphitems: C{dict}
    @param h: host
    @param h: C{Host}
    @returns: None
    """
    for name, graph in graphitems.iteritems():
        g = DBSession.query(Graph).filter(Graph.name == name).first()
        g.template = graph['template']
        g.vlabel = graph['vlabel']
    
    DBSession.flush()


if __name__ == "__main__":
    syslog.openlog('DBExportator' , syslog.LOG_PERROR)
    syslog.syslog(syslog.LOG_INFO, "DBExportator Begin")

    try:
        conf.loadConf()
    except Exception,e :
        syslog.syslog(syslog.LOG_ERR, "Cannot load the conf.")
        syslog.syslog(syslog.LOG_ERR, str(e) )
        sys.exit(-1)

    export_conf_db()
    
    syslog.syslog(syslog.LOG_INFO, "DBExportator End")

def export_ventilation_DB(ventilation):
    """Export ventilation in DB
    @param ventilation: dict generated by findAServerForEachHost
    @type ventilation: C{dict}
    
    Example:
      >>> findAServerForEachHost()
      {
      ...
      "my_host_name":
        {
          'apacheRP': 'presentation_server.domain.name',
          'collector': 'collect_server_pool1.domain.name',
          'corrsup': 'correlation_server.domain.name',
          'corrtrap': 'correlation_server.domain.name',
          'dns': 'infra_server.domain.name',
          'nagios': 'collect_server_pool1.domain.name',
          'nagvis': 'presentation_server.domain.name',
          'perfdata': 'collect_server_pool1.domain.name',
          'rrdgraph': 'store_server_pool2.domain.name',
          'storeme': 'store_server_pool2.domain.name',
          'supnav': 'presentation_server.domain.name'
        }
      ...
      }
    
    """
    # delete all associations
    DBSession.query(HostApplication).delete()
    
    for host, serverbyapp in ventilation.iteritems():
        for app, server in serverbyapp.iteritems():
            hostapp = HostApplication(host=Host.by_host_name(host),
                                      appserver=Host.by_host_name(server),
                                      application=Application.by_app_name(app))
    
    DBSession.flush()

