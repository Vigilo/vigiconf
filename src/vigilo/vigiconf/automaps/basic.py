#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Générateur de cartes automatiques basique.

"""
from . import AutoMap

from vigilo.models.tables import MapNodeHost, MapNodeHls, MapNodeLls
from vigilo.models.session import DBSession

from sqlalchemy import and_

class BasicAutoMap(AutoMap):
    
    top_groups = [ u'Groupes',
                   u'%(hostgroup)s',
                   u'Frégate',
                   u'Porte-avion',
                   u'Sous-marin nucléaire lanceur d\'engins',
                   u'Sous-marin nucléaire d\'attaque',
                   u'Bâtiment de projection et de commandement',
                   u'Pétrolier ravitailleur' ,
                   u'Chasseur de mines']
    
    parent_topgroups = None
    
    map_groups = ['Groupes',]
    
    def process_top_group(self, group):
        """ génération des entités liées à un groupe d'hosts de niveau supérieur.
        
        TODO: spec, rm context
        """
        # génération des MapGroup
        for name in self.top_groups:
            gname = name % {'hostgroup':group.name}
            gmap = self.get_or_create_mapgroup(gname, parent_name=self.parent_topgroups)
        
        # génération des Map
        self.generate_maps(group, mapgroups=self.map_groups)
    
    def process_leaf_group(self, group):
        # on fait comme pour les top groups
        self.process_top_group(group)
        # on fait la hiérarchie des mapgroup
        map = Map.by_map_title(group.name)
        if map:
            if group.has_parent():
                map.groups = [self.get_groupmap(group.get_parent()),]
    
    def generate_maps(self, group, mapgroups=[]):
        nbelts = len(group.get_hosts()) + len(group.get_services())
        if nbelts > 0:
            map = Map.by_map_title(group.name)
            created = False
            if not map:
                map = self.create_map(group.name, mapgroups, map_defaults)
                created = True
            if map.generated:
                # on gère le contenu uniquement pour les cartes auto
                self.populate_map(map, group, map_defaults, created=created)
        
        DBSession.flush()
        
    def populate_map(self, map, group, data, created=True):
        """ ajout de contenu dans une carte
        """
        # ajout des nodes hosts
        hosts = list(group.get_hosts())
        for host in hosts:
            # on regarde si un node existe
            nodes = DBSession.query(MapNodeHost).filter(
                                            and_(MapNodeHost.map == map,
                                                 MapNodeHost.host == host)
                                            ).all()
            if not nodes:
                node = MapNodeHost(label=host.name,
                                   map=map,
                                   host=host,
                                   widget=u"ServiceElement",
                                   icon=data['host_icon'])
                DBSession.add(node)
            else:
                if len(nodes) > 1:
                    raise Exception("host has more than one node in a map")
                # on ne fait rien sur ls éléments présents
        
        # ajout des nodes services
        services = list(group.get_services())
        for service in services:
            # on regarde si un node existe
            nodes = DBSession.query(MapNodeHls).filter(
                                        and_(MapNodeHls.map == map,
                                             MapNodeHls.service == service)
                                            ).all()
            
            if not nodes:
                node = MapNodeHls(label=service.servicename,
                                    map=map,
                                    service=service,
                                    widget=u"ServiceElement",
                                    icon=data['hls_icon'])
                DBSession.add(node)
            else:
                if len(nodes) > 1:
                    raise Exception("service Hls has more than one node in a map")
                # on ne fait rien sur ls éléments présents
        
        # on supprime les éléments qui ne font pas partie des éléments
        # qu'on devrait ajouter (on fait ça seulement pour les cartes auto)
        if map.generated:
            nodes = DBSession.query(MapNodeHost)\
                        .filter(MapNodeHost.map == map)
            # nodes dont les hosts ne font plus partie du groupe group
            for node in nodes:
                if not node.host in hosts:
                    DBSession.delete(node)
            
            nodes = DBSession.query(MapNodeHls)\
                        .filter(MapNodeHls.map == map)
            # nodes dont les services ne font plus partie du groupe group
            for node in nodes:
                if not node.service in services:
                    DBSession.delete(node)
