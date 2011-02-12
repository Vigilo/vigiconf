# -*- coding: utf-8 -*-
################################################################################
#
# VigiConf
# Copyright (C) 2007-2011 CS-SI
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

# pylint: disable-msg=E1101

"""
Module in charge of finding the good server to handle a given application
for a given host defined in the configuration.

This file is part of the Enterprise Edition
"""

from __future__ import absolute_import

import transaction
import zlib

from vigilo.models.session import DBSession
from vigilo.models import tables

from vigilo.common.logging import get_logger
LOGGER = get_logger(__name__)

from vigilo.common.gettext import translate
_ = translate(__name__)

from vigilo.vigiconf import conf
from vigilo.vigiconf.lib.exceptions import ParsingError, VigiConfError
from vigilo.vigiconf.lib.ventilation import Ventilator


__docformat__ = "epytext"
__all__ = ("VentilatorRemote", "NoServerAvailable")

_CACHE = {
    "host": {},
    "active_vservers": [],
    }

class NoServerAvailable(VigiConfError):
    """
    Exception remontée quand il n'y a pas de serveur Vigilo où ventiler un
    groupe d'hôtes
    """
    pass

class VentilatorRemote(Ventilator):

    def __init__(self, apps):
        super(VentilatorRemote, self).__init__(apps)
        self.apps_by_appgroup = self.get_app_by_appgroup()

    def appendHost(self, vservername, hostname, appgroup):
        """
        Append a host to the database
        @param vservername: Vigilo server name
        @type  vservername: C{str}
        @param hostname: the host to append
        @type  hostname: C{str}
        """
        vserver = tables.VigiloServer.by_vigiloserver_name(unicode(vservername))
        host = tables.Host.by_host_name(unicode(hostname))
        for app in self.apps_by_appgroup[appgroup]:
            application = tables.Application.by_app_name(unicode(app.name))
            if not application:
                raise VigiConfError(_("Can't find application %s in database")
                                    % app.name)
            DBSession.add(tables.Ventilation(
                                vigiloserver=vserver,
                                host=host,
                                application=application,
                          ))
        DBSession.flush()

    def get_previous_servers(self, host, appgroup):
        """
        Retourne le nom des précédents serveurs Vigilo
        sur lequel l'hôte a été ventilé pour une
        application précise.

        @param  host: Nom de l'hôte dont on veut connaître
            la ventilation précédente.
        @type   host: C{str}
        @param  appgroup: Nom de l'application dont la ventilation
            nous intéresse.
        @type   appgroup: C{str}
        @return: Nom des serveurs Vigilo sur lequels l'hôte L{host}
            a été ventilé pour l'application L{appgroup}.
        @rtype: C{list} of C{str}
        """
        apps = [unicode(app.name) for app in self.apps_by_appgroup[appgroup]]
        if host not in _CACHE["host"]:
            host_db = tables.Host.by_host_name(unicode(host))
            _CACHE["host"][host] = host_db.idhost
        prev_servers = DBSession.query(
                tables.VigiloServer.name
            ).join(
                tables.Ventilation,
                (tables.Application,
                    tables.Ventilation.idapp == tables.Application.idapp),
            ).filter(tables.Application.name.in_(apps)
            ).filter(tables.Ventilation.idhost == _CACHE["host"][host]
            ).filter(tables.VigiloServer.disabled == False
            ).all()
        return [server.name for server in prev_servers]

    def get_host_ventilation_group(self, hostname, hostdata):
        if "serverGroup" in hostdata and hostdata["serverGroup"]:
            if hostdata["serverGroup"].count("/") == 1:
                hostdata["serverGroup"] = hostdata["serverGroup"].lstrip("/")
            return hostdata["serverGroup"]
        groups = set()
        host = tables.Host.by_host_name(unicode(hostname))
        if not host:
            raise KeyError("Trying to ventilate host %s, but it's not in the "
                           "database yet" % hostname)
        for group in host.groups:
            groups.add(group.get_top_parent().name)

        if not groups:
            raise ParsingError(_('Could not determine how to '
                'ventilate host "%s". Affect some groups to '
                'this host or use the ventilation attribute.') %
                hostname)

        if len(groups) != 1:
            raise ParsingError(_('Found multiple candidates for '
                    'ventilation (%(candidates)r) on "%(host)s", '
                    'use the ventilation attribute to select one.') % {
                    'candidates': u', '.join([unicode(g) for g in groups]),
                    'host': hostname,
                })
        ventilation = groups.pop()
        if ventilation.count("/") == 1:
            ventilation = ventilation.lstrip("/")
        hostdata['serverGroup'] = ventilation
        return ventilation

    def get_app_by_appgroup(self):
        appgroups = {}
        for app in self.apps:
            appgroups.setdefault(app.group, []).append(app)
        return appgroups

    def filter_vservers(self, vserverlist):
        """
        Filtre une liste pour ne garder que les serveurs qui ne sont pas
        désactivés.
        @param vserverlist: list de noms de serveurs Vigilo
        @type  vserverlist: C{list} de C{str}
        """
        if not _CACHE["active_vservers"]:
            # on construit le cache
            for vserver in DBSession.query(tables.VigiloServer).all():
                if not vserver.disabled:
                    _CACHE["active_vservers"].append(vserver.name)
        return [ v for v in vserverlist if v in _CACHE["active_vservers"] ]

    def ventilate(self):
        """
        Try to find the best server where to monitor the hosts contained in the
        I{conf}.

        @return: a dict of the ventilation result. The dict content is:
          - B{Key}: name of a host
          - B{value}: a dict in the form:
            - B{Key}: the name of an application for which we have to deploy a
              configuration for this host
              (Nagios, CorrSup, Collector...)
            - B{Value}: the hostname of the server where to deploy the conf for
              this host and this application

        I{Example}:

          >>> ventilate()
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
        LOGGER.debug("Ventilation begin")

        # On collecte tous les groupes d'hôtes
        hostgroups = {}
        for (host, v) in conf.hostsConf.iteritems():
            hostgroup = self.get_host_ventilation_group(host, v)
            if hostgroup not in hostgroups:
                hostgroups[hostgroup] = []
            hostgroups[hostgroup].append(host)

        # On calcule les pools de ventilation pour chaque groupe d'application,
        # en prenant en compte les serveurs désactivés et le backup
        errors = set()
        r = {}
        for hostgroup, hosts in hostgroups.iteritems():
            for host in hosts:
                app_to_vservers = {}
                for appgroup in conf.appsGroupsByServer:
                    # On essaye de récupérer les serveurs Vigilo
                    # sur lesquels on peut ventiler. Il peut y en
                    # avoir 2 (un nominal et un backup) ou un seul
                    # (un backup) si tous les nominaux sont tombés.
                    try:
                        servers = self._ventilate_appgroup(appgroup, hostgroup, host)
                    except NoServerAvailable, e:
                        errors.add(e.value)
                        continue
                    if servers is None:
                        continue
                    for app in self.apps_by_appgroup[appgroup]:
                        app_to_vservers[app] = servers
                r[host] = app_to_vservers

        for error in errors:
            LOGGER.warning(_("No server available for the appgroup %(appgroup)s"
                             " and the hostgroup %(hostgroup)s, skipping it"),
                           {"appgroup": error[0], "hostgroup": error[1]})

        #from pprint import pprint; pprint(r)
        LOGGER.debug("Ventilation end")
        return r

    def _ventilate_appgroup(self, appGroup, hostGroup, host):
        if appGroup not in self.apps_by_appgroup or \
                not self.apps_by_appgroup[appGroup]:
            return None # pas d'appli dans ce groupe

        vservers = []
        checksum = zlib.adler32(host)

        # On regarde quels sont les serveurs nominaux disponibles.
        nominal = conf.appsGroupsByServer[appGroup][hostGroup]
        nominal = self.filter_vservers(nominal) # ne garde que les actifs
        previous_servers = set(self.get_previous_servers(host, appGroup))

        # Parmi tous les serveurs Vigilo nominaux disponibles,
        # on en choisit un.
        if nominal:
            intersect = previous_servers & set(nominal)
            if intersect:
                vservers.append(intersect.pop())
            else:
                vservers.append(nominal[checksum % len(nominal)])

        # On regarde les serveurs de backup utilisables.
        backup_mapping = getattr(conf, "appsGroupsBackup", {})
        if appGroup in backup_mapping and \
                hostGroup in backup_mapping[appGroup]:
            backup = backup_mapping[appGroup][hostGroup]
            backup = self.filter_vservers(backup)

            if backup:
                intersect = previous_servers & set(backup)
                if intersect:
                    vservers.append(intersect.pop())
                else:
                    vservers.append(backup[checksum % len(backup)])

        if not vservers:
            # Aucun serveur disponible, même dans le backup.
            # On abandonne.
            raise NoServerAvailable((appGroup, hostGroup))
        return vservers


    # Gestion des serveurs Vigilo

    def disable_server(self, vservername):
        """
        Désactive un serveur Vigilo
        @param vservername: nom du serveur Vigilo
        @type  vservername: C{str}
        """
        vserver = tables.VigiloServer.by_vigiloserver_name(unicode(vservername))
        if vserver is None:
            raise VigiConfError(_("The Vigilo server %s does not exist")
                                % vservername)
        if vserver.disabled:
            raise VigiConfError(_("The Vigilo server %s is already disabled")
                                % vservername)
        vserver.disabled = True
        DBSession.flush()
        transaction.commit()

    def enable_server(self, vservername):
        """
        Active un serveur Vigilo
        @param vservername: nom du serveur Vigilo
        @type  vservername: C{str}
        """
        vserver = tables.VigiloServer.by_vigiloserver_name(unicode(vservername))
        if vserver is None:
            raise VigiConfError(_("The Vigilo server %s does not exist")
                                % vservername)
        if not vserver.disabled:
            raise VigiConfError(_("The Vigilo server %s is already enabled")
                                % vservername)
        # On efface les associations précédentes
        prev_ventil = DBSession.query(
                    tables.Ventilation.idapp, tables.Ventilation.idhost
                ).filter(
                    tables.Ventilation.idvigiloserver == vserver.idvigiloserver
                ).all()
        for idapp, idhost in prev_ventil:
            temp_ventils = DBSession.query(tables.Ventilation
                ).filter(
                    tables.Ventilation.idapp == idapp
                ).filter(
                    tables.Ventilation.idhost == idhost
                ).filter(
                    tables.Ventilation.idvigiloserver != vserver.idvigiloserver
                ).all()
            for temp_ventil in temp_ventils:
                DBSession.delete(temp_ventil)
        vserver.disabled = False
        DBSession.flush()
        transaction.commit()


# vim:set expandtab tabstop=4 shiftwidth=4:
