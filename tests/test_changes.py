#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gestion du changement lors du chargement de

 - Dependency
"""

import unittest

from vigilo.vigiconf.loaders.dependency import DependencyLoader

import vigilo.vigiconf.conf as conf
from confutil import reload_conf, setup_db, teardown_db

from vigilo.models.tables import Host
from vigilo.models.tables import LowLevelService, HighLevelService, Dependency

from vigilo.models.session import DBSession

class ChangeManagementTest(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""
        reload_conf()
        setup_db()
        self.dependencyloader = DependencyLoader()

        # Présents dans les fichiers XML
        localhost =  Host(
            name=u'localhost',
            checkhostcmd=u'halt -f',
            snmpcommunity=u'public',
            description=u'my localhost',
            hosttpl=u'template',
            address=u'127.0.0.1',
            snmpport=124,
            weight=44,
        )
        DBSession.add(localhost)
        hlservice1 = HighLevelService(
            servicename=u'hlservice1',
            op_dep=u'+',
            message=u'Hello world',
            warning_threshold=50,
            critical_threshold=80,
            priority=1
        )
        DBSession.add(hlservice1)
        interface = LowLevelService(
            servicename=u'Interface eth0',
            op_dep=u'+',
            weight=100,
            host=localhost
        )
        DBSession.add(interface)
        
        # Pour les tests
        self.testhost1 =  Host(
            name=u'test_change_deps_1',
            checkhostcmd=u'halt -f',
            snmpcommunity=u'public',
            description=u'my localhost',
            hosttpl=u'template',
            address=u'127.0.0.1',
            snmpport=42,
            weight=42,
        )
        DBSession.add(self.testhost1)
        self.testhost2 =  Host(
            name=u'test_change_deps_2',
            checkhostcmd=u'halt -f',
            snmpcommunity=u'public',
            description=u'my localhost',
            hosttpl=u'template',
            address=u'127.0.0.1',
            snmpport=42,
            weight=42,
        )
        DBSession.add(self.testhost2)
        DBSession.flush()
        
    def tearDown(self):
        """Call after every test case."""
        teardown_db()

    
    def test_change_dependencies_suppr(self):
        """ Test de la gestion des changements des dépendances.
        """
        self.dependencyloader.load()
        dep = Dependency(supitem1=self.testhost1, supitem2=self.testhost2)
        DBSession.add(dep)
        DBSession.flush()
        depnum_before = DBSession.query(Dependency).count()
        self.dependencyloader.load()
        depnum_after = DBSession.query(Dependency).count()
        self.assertEquals(depnum_after, depnum_before - 1)
        
    def test_change_dependencies_add(self):
        self.dependencyloader.load()
        DBSession.delete( DBSession.query(Dependency).all()[0] )
        DBSession.flush()
        depnum_before = DBSession.query(Dependency).count()
        self.dependencyloader.load()
        depnum_after = DBSession.query(Dependency).count()
        self.assertEquals(depnum_after, depnum_before + 1)
        
    def test_change_dependencies_nothing(self):
        self.dependencyloader.load()
        depnum_before = DBSession.query(Dependency).count()
        self.dependencyloader.load()
        depnum_after = DBSession.query(Dependency).count()
        self.assertEquals(depnum_after, depnum_before)

