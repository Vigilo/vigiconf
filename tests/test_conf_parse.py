#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, unittest, tempfile, shutil, glob, subprocess

from vigilo.common.conf import settings
settings.load_module(__name__)

import vigilo.vigiconf.conf as conf
from vigilo.vigiconf.lib.confclasses.host import Host
from vigilo.vigiconf.lib import ParsingError
from vigilo.vigiconf.loaders.group import GroupLoader

from confutil import reload_conf, setup_tmpdir, setup_path
from confutil import setup_db, teardown_db

class ValidateXSD(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""
        self.dtddir = os.path.join(conf.CODEDIR, "validation", "xsd")
        self.hdir = os.path.join(settings["vigiconf"].get("confdir"), "hosts")
        self.htdir = os.path.join(settings["vigiconf"].get("confdir"),
                        "hosttemplates")

    def test_host(self):
        """Validate the provided hosts against the XSD"""
        devnull = open("/dev/null", "w")
        hosts = glob.glob(os.path.join(self.hdir, "*.xml"))
        for host in hosts:
            valid = subprocess.call(["xmllint", "--noout", "--schema",
                                    os.path.join(self.dtddir, "host.xsd"), host],
                                    stdout=devnull, stderr=subprocess.STDOUT)
            self.assertEquals(valid, 0, "Validation of host \"%s\" failed" % os.path.basename(host))
        devnull.close()

    def test_hosttemplate(self):
        """Validate the provided hosttemplatess against the XSD"""
        devnull = open("/dev/null", "w")
        hts = glob.glob(os.path.join(self.htdir, "*.xml"))
        for ht in hts:
            valid = subprocess.call(["xmllint", "--noout", "--schema",
                                    os.path.join(self.dtddir, "hosttemplate.xsd"), ht],
                                    stdout=devnull, stderr=subprocess.STDOUT)
            self.assertEquals(valid, 0, "Validation of hosttemplate \"%s\" failed" % os.path.basename(ht))
        devnull.close()


class ParseHost(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""
        # Prepare temporary directory
        setup_db()
        self.tmpdir = setup_tmpdir()
        shutil.copytree(os.path.join(
                            settings["vigiconf"].get("confdir"), "general"),
                        os.path.join(self.tmpdir, "general"))
        shutil.copytree(os.path.join(
                        settings["vigiconf"].get("confdir"), "hosttemplates"),
                        os.path.join(self.tmpdir, "hosttemplates"))
        shutil.copytree(os.path.join(
                        settings["vigiconf"].get("confdir"), "groups"),
                        os.path.join(self.tmpdir, "groups"))
        os.mkdir(os.path.join(self.tmpdir, "hosts"))
        settings["vigiconf"]["confdir"] = self.tmpdir
        # We changed the paths, reload the factories
        reload_conf()
        self.host = open(os.path.join(self.tmpdir, "hosts", "host.xml"), "w")

    def tearDown(self):
        """Call after every test case."""
        # This has been overwritten in setUp, reset it
        setup_path()
        #settings["vigiconf"]["confdir"] = os.path.join(os.path.dirname(__file__), "..", "src", "conf.d")
        shutil.rmtree(self.tmpdir)
        teardown_db()

    def test_host(self):
        """Test the parsing of a basic host declaration"""
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <group>/Servers/Linux servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        assert conf.hostsConf.has_key("testserver1"), \
                "host is not properly parsed"
        assert conf.hostsConf["testserver1"]["name"] == "testserver1", \
                "host name is not properly parsed"
        assert conf.hostsConf["testserver1"]["address"] == "192.168.1.1", \
                "host address is not properly parsed"
        assert conf.hostsConf["testserver1"]["serverGroup"] == "Servers", \
                "host main group is not properly parsed"

    def test_host_whitespace(self):
        """Test the handling of whitespaces in a basic host declaration"""
        self.host.write("""<?xml version="1.0"?>
        <host name=" testserver1 " address=" 192.168.1.1 " ventilation=" Servers ">
            <group>/Servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assert_(conf.hostsConf.has_key("testserver1"),
                     "host parsing does not handle whitespaces properly")

    def test_template(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <template>linux</template>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assert_("Linux servers" in conf.hostsConf["testserver1"]["otherGroups"],
                     "The \"template\" tag is not properly parsed")

    def test_template_whitespace(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <template> linux </template>
        </host>""")
        self.host.close()
        try:
            conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        except KeyError:
            self.fail("The \"template\" tag does not strip whitespaces")
        self.assert_("Linux servers" in conf.hostsConf["testserver1"]["otherGroups"],
                     "The \"template\" tag is not properly parsed")

    def test_attribute(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <attribute name="cpulist">2</attribute>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assert_(conf.hostsConf["testserver1"].has_key("cpulist") and 
                     conf.hostsConf["testserver1"]["cpulist"] == "2",
                     "The \"attribute\" tag is not properly parsed")

    def test_attribute_whitespace(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <attribute name=" cpulist "> 2 </attribute>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        assert conf.hostsConf["testserver1"].has_key("cpulist") and \
                conf.hostsConf["testserver1"]["cpulist"] == "2", \
                "The \"attribute\" tag parsing does not strip whitespaces"

    def test_tag_host(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <tag service="Host" name="important">2</tag>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        assert "tags" in conf.hostsConf["testserver1"] and \
               "important" in conf.hostsConf["testserver1"]["tags"] and \
                conf.hostsConf["testserver1"]["tags"]["important"] == "2", \
                "The \"tag\" tag for hosts is not properly parsed"

    def test_tag_service(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <tag service="UpTime" name="important">2</tag>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        assert "tags" in conf.hostsConf["testserver1"]["services"]["UpTime"] and \
               "important" in conf.hostsConf["testserver1"]["services"]["UpTime"]["tags"] and \
               conf.hostsConf["testserver1"]["services"]["UpTime"]["tags"]["important"] == "2", \
               "The \"tag\" tag for services is not properly parsed"

    def test_tag_whitespace(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <tag service=" Host " name=" important "> 2 </tag>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        try:
            conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        except KeyError:
            self.fail("The \"tag\" tag parsing does not strip whitespaces")
        assert "tags" in conf.hostsConf["testserver1"] and \
               "important" in conf.hostsConf["testserver1"]["tags"] and \
               conf.hostsConf["testserver1"]["tags"]["important"] == "2", \
               "The \"tag\" tag parsing does not strip whitespaces"

    def test_trap(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <trap service="test.add_trap" key="test.name">test.label</trap>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        assert conf.hostsConf["testserver1"].has_key("trapItems") and \
                conf.hostsConf["testserver1"]["trapItems"]["test.add_trap"]["test.name"] == "test.label", \
                "The \"trap\" tag is not properly parsed"

    def test_trap_whitespace(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <trap service=" test.add_trap " key=" test.name "> test.label </trap>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        assert "trapItems" in conf.hostsConf["testserver1"] and \
               "test.add_trap" in conf.hostsConf["testserver1"]["trapItems"] and \
               "test.name" in conf.hostsConf["testserver1"]["trapItems"]["test.add_trap"] and \
               conf.hostsConf["testserver1"]["trapItems"]["test.add_trap"]["test.name"] == "test.label", \
               "The \"trap\" tag parsing does not strip whitespaces"

    def test_group(self):
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <group>Linux servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assert_("Linux servers" in conf.hostsConf["testserver1"]["otherGroups"],
                     "The \"group\" tag is not properly parsed")

    def test_group_whitespace(self):
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <group> Linux servers </group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assert_("Linux servers" in conf.hostsConf["testserver1"]["otherGroups"],
                     "The \"group\" tag parsing does not strip whitespaces")

    def test_group_multiple(self):
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <group>Linux servers</group>
            <group>AIX servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assert_("Linux servers" in conf.hostsConf["testserver1"]["otherGroups"]
                 and "AIX servers" in conf.hostsConf["testserver1"]["otherGroups"],
                 "The \"group\" tag does not handle multiple values")

    def test_test(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
        <test name="Interface">
            <arg name="label">eth0</arg>
            <arg name="ifname">eth0</arg>
            <group>/Servers</group>
        </test>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        assert ('Interface eth0', 'service') in conf.hostsConf["testserver1"]["SNMPJobs"], \
                "The \"test\" tag is not properly parsed"

    def test_test_whitespace(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
        <test name=" Interface ">
            <arg name=" label "> eth0 </arg>
            <arg name=" ifname "> eth0 </arg>
            <group>/Servers</group>
        </test>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        assert ('Interface eth0', 'service') in conf.hostsConf["testserver1"]["SNMPJobs"], \
                "The \"test\" tag parsing does not strip whitespaces"

    def test_test_weight(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" ventilation="Servers">
        <test name="Interface" weight="42">
            <arg name="label">eth0</arg>
            <arg name="ifname">eth0</arg>
            <group>/Servers</group>
        </test>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        #from pprint import pprint; pprint(conf.hostsConf["testserver1"])
        self.assert_("weight" in conf.hostsConf["testserver1"]["services"]["Interface eth0"],
                     "L'attribut weight du test n'est pas chargé")
        self.assertEquals(conf.hostsConf["testserver1"]["services"]["Interface eth0"]["weight"], 42,
                          "L'attribut weight n'a pas la bonne valeur")

    def test_test_weight_default(self):
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" ventilation="Servers">
        <test name="Interface">
            <arg name="label">eth0</arg>
            <arg name="ifname">eth0</arg>
            <group>/Servers</group>
        </test>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assertEquals(conf.hostsConf["testserver1"]["services"]["Interface eth0"]["weight"], 1,
                          "L'attribut weight n'a pas la bonne valeur par défaut")

    def test_test_weight_invalid(self):
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" ventilation="Servers">
        <test name="Interface" weight="invalid">
            <arg name="label">eth0</arg>
            <arg name="ifname">eth0</arg>
        </test>
        </host>""")
        self.host.close()
        filepath = os.path.join(self.tmpdir, "hosts", "host.xml")
        self.assertRaises(ParsingError, conf.hostfactory._loadhosts, filepath)

    def test_ventilation_explicit_server(self):
        """Ventilation en utilisant un groupe explicitement nommé."""
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="foo" address="127.0.0.1" ventilation="P-F">
            <arg name="label">eth0</arg>
            <arg name="ifname">eth0</arg>
            <group>/Servers/Linux servers</group>
        </host>
        """)
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        # L'attribut ventilation a été donné explicitement.
        self.assertEqual(conf.hostsConf['foo']['serverGroup'], 'P-F')

    def test_missing_group_association(self):
        """Hôte associé à aucun groupe opérationnel."""
        self.host.write("""<?xml version="1.0"?>
        <host name="foo" address="127.0.0.1" ventilation="P-F">
            <arg name="label">eth0</arg>
            <arg name="ifname">eth0</arg>
        </host>
        """)
        self.host.close()
        # Un hôte doit toujours être associé à au moins un <group>.
        # La vérification ne peut pas être faite au niveau du schéma XSD
        # car on perdrait alors la possibilité d'utiliser un ordre quelconque
        # pour les balises de définition d'un hôte.
        self.assertRaises(ParsingError, conf.hostfactory._loadhosts,
            os.path.join(self.tmpdir, "hosts", "host.xml"))

    def test_test_missing_args(self):
        """Ajout d'un test auquel il manque des arguments sur un hôte."""
        # Le test "TCP" nécessite normalement un argument "port".
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <test name="TCP"/>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        # Une exception TypeError indiquant qu'il n'y pas assez d'arguments
        # doit être levée.
        self.assertRaises(TypeError,
            conf.hostfactory._loadhosts,
            os.path.join(self.tmpdir, "hosts", "host.xml")
        )

    def test_test_additional_args(self):
        """Ajout d'un test avec trop d'arguments sur un hôte."""
        # Le test "TCP" n'accepte pas d'argument "unknown".
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1" address="192.168.1.1" ventilation="Servers">
            <test name="TCP">
                <arg name="port">1234</arg>
                <arg name="unknown_arg"> ... </arg>
            </test>
            <group>/Servers</group>
        </host>""")
        self.host.close()
        # Une exception TypeError indiquant qu'un paramètre inconnu
        # a été passé doit être levée.
        self.assertRaises(TypeError,
            conf.hostfactory._loadhosts,
            os.path.join(self.tmpdir, "hosts", "host.xml")
        )

    def test_host_weight(self):
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1">
            <weight>42</weight>
            <group>/Servers/Linux servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assert_("weight" in conf.hostsConf["testserver1"],
                     "L'attribut weight n'est pas chargé")
        self.assertEquals(conf.hostsConf["testserver1"]["weight"], 42,
                          "L'attribut weight n'a pas la bonne valeur")

    def test_host_weight_default(self):
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1">
            <group>/Servers/Linux servers</group>
        </host>""")
        self.host.close()
        conf.hostfactory._loadhosts(os.path.join(self.tmpdir, "hosts", "host.xml"))
        self.assert_("weight" in conf.hostsConf["testserver1"],
                     "L'attribut weight n'est pas réglé par défaut")
        self.assertEquals(conf.hostsConf["testserver1"]["weight"], 1,
                          "L'attribut weight n'a pas la bonne valeur par défaut")

    def test_host_weight_invalid(self):
        GroupLoader().load()
        self.host.write("""<?xml version="1.0"?>
        <host name="testserver1">
            <weight>invalid</weight>
            <group>/Servers/Linux servers</group>
        </host>""")
        self.host.close()
        filepath = os.path.join(self.tmpdir, "hosts", "host.xml")
        self.assertRaises(ParsingError, conf.hostfactory._loadhosts, filepath)


class ParseHostTemplate(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""
        # Prepare temporary directory
        setup_db()
        self.tmpdir = setup_tmpdir()
        shutil.copytree(os.path.join(
                            settings["vigiconf"].get("confdir"), "general"),
                        os.path.join(self.tmpdir, "general"))
        #shutil.copytree(os.path.join(
        #                    settings["vigiconf"].get("confdir"), "hosttemplates"),
        #                os.path.join(self.tmpdir, "hosttemplates"))
        os.mkdir(os.path.join(self.tmpdir, "hosttemplates"))
        os.mkdir(os.path.join(self.tmpdir, "hosts"))
        settings["vigiconf"]["confdir"] = self.tmpdir
        # We changed the paths, reload the factories
        reload_conf()
        conf.hosttemplatefactory.path = [os.path.join(self.tmpdir, "hosttemplates"),]
        self.defaultht = open(os.path.join(self.tmpdir, "hosttemplates", "default.xml"), "w")
        self.defaultht.write('<?xml version="1.0"?>\n<templates><template name="default"></template></templates>')
        self.defaultht.close()
        self.ht = open(os.path.join(self.tmpdir, "hosttemplates", "test.xml"), "w")

    def tearDown(self):
        """Call after every test case."""
        # This has been overwritten in setUp, reset it
        setup_path()
        shutil.rmtree(self.tmpdir)
        teardown_db()

    def test_template(self):
        """Test the parsing of a basic template declaration"""
        self.ht.write("""<?xml version="1.0"?>\n<templates><template name="test"></template></templates>""")
        self.ht.close()
        try:
            conf.hosttemplatefactory.load_templates()
        except KeyError:
            self.fail("template is not properly parsed")
        assert "test" in conf.hosttemplatefactory.templates, \
               "template is not properly parsed"

    def test_template_whitespace(self):
        self.ht.write("""<?xml version="1.0"?>\n<templates><template name=" test "></template></templates>""")
        self.ht.close()
        try:
            conf.hosttemplatefactory.load_templates()
        except KeyError:
            self.fail("template parsing does not strip whitespaces")
        assert "test" in conf.hosttemplatefactory.templates, \
               "template parsing does not strip whitespaces"

    def test_attribute(self):
        self.ht.write("""<?xml version="1.0"?>
                <templates>
                    <template name="test">
                        <attribute name="testattr">testattrvalue</attribute>
                    </template>
                </templates>""")
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        assert "testattr" in conf.hosttemplatefactory.templates["test"]["attributes"] and \
               conf.hosttemplatefactory.templates["test"]["attributes"]["testattr"] == "testattrvalue", \
               "The \"attribute\" tag is not properly parsed"

    def test_attribute_whitespace(self):
        self.ht.write("""<?xml version="1.0"?>
                <templates>
                    <template name="test">
                        <attribute name=" testattr "> testattrvalue </attribute>
                    </template>
                </templates>
                """)
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        assert "testattr" in conf.hosttemplatefactory.templates["test"]["attributes"] and \
               conf.hosttemplatefactory.templates["test"]["attributes"]["testattr"] == "testattrvalue", \
               "The \"attribute\" tag parsing does not strip whitespaces"

    def test_test(self):
        self.ht.write("""<?xml version="1.0"?>
                <templates>
                <template name="test">
                    <test name="TestTest"/>
                </template>
                </templates>""")
        self.ht.close()
        try:
            conf.hosttemplatefactory.load_templates()
        except KeyError:
            self.fail("The \"test\" tag is not properly parsed")
        self.assertEquals("TestTest",
               conf.hosttemplatefactory.templates["test"]["tests"][0]["name"],
               "The \"test\" tag is not properly parsed")

    def test_test_args(self):
        self.ht.write("""<?xml version="1.0"?>
                <templates>
                <template name="test">
                    <test name="TestTest">
                        <arg name="TestArg1">TestValue1</arg>
                        <arg name="TestArg2">TestValue2</arg>
                    </test>
                </template>
                </templates>""")
        self.ht.close()
        try:
            conf.hosttemplatefactory.load_templates()
        except KeyError:
            self.fail("The \"test\" tag with arguments is not properly parsed")
        assert len(conf.hosttemplatefactory.templates["test"]["tests"]) == 1 and \
               conf.hosttemplatefactory.templates["test"]["tests"][0]["name"] == "TestTest" and \
               "TestArg1" in conf.hosttemplatefactory.templates["test"]["tests"][0]["args"] and \
               "TestArg2" in conf.hosttemplatefactory.templates["test"]["tests"][0]["args"] and \
               conf.hosttemplatefactory.templates["test"]["tests"][0]["args"]["TestArg1"] == "TestValue1" and \
               conf.hosttemplatefactory.templates["test"]["tests"][0]["args"]["TestArg2"] == "TestValue2", \
               "The \"test\" tag with arguments is not properly parsed"

    def test_test_whitespace(self):
        self.ht.write("""<?xml version="1.0"?>
                <templates>
                <template name="test">
                    <test name=" TestTest ">
                        <arg name=" TestArg1 "> TestValue1 </arg>
                        <arg name=" TestArg2 "> TestValue2 </arg>
                    </test>
                </template>
                </templates>""")
        self.ht.close()
        try:
            conf.hosttemplatefactory.load_templates()
        except KeyError:
            self.fail("The \"test\" tag parsing does not strip whitespaces")
        assert len(conf.hosttemplatefactory.templates["test"]["tests"]) == 1 and \
               conf.hosttemplatefactory.templates["test"]["tests"][0]["name"] == "TestTest" and \
               "TestArg1" in conf.hosttemplatefactory.templates["test"]["tests"][0]["args"] and \
               "TestArg2" in conf.hosttemplatefactory.templates["test"]["tests"][0]["args"] and \
               conf.hosttemplatefactory.templates["test"]["tests"][0]["args"]["TestArg1"] == "TestValue1" and \
               conf.hosttemplatefactory.templates["test"]["tests"][0]["args"]["TestArg2"] == "TestValue2", \
               "The \"test\" tag parsing does not strip whitespaces"

    def test_test_weight(self):
        self.ht.write("""<?xml version="1.0"?>
        <templates>
        <template name="testtemplate">
            <test name="TestTest" weight="42">
                <arg name="TestArg1">TestValue1</arg>
                <arg name="TestArg2">TestValue2</arg>
            </test>
        </template>
        </templates>""")
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        self.assert_("weight" in conf.hosttemplatefactory.templates["testtemplate"]["tests"][0],
                     "L'attribut weight du test n'est pas chargé")
        self.assertEquals(
                conf.hosttemplatefactory.templates["testtemplate"]["tests"][0]["weight"],
                42, "L'attribut weight n'a pas la bonne valeur")

    def test_test_weight_default(self):
        self.ht.write("""<?xml version="1.0"?>
        <templates>
        <template name="testtemplate">
            <test name="TestTest">
                <arg name="TestArg1">TestValue1</arg>
                <arg name="TestArg2">TestValue2</arg>
            </test>
        </template>
        </templates>""")
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        self.assertEquals(
                conf.hosttemplatefactory.templates["testtemplate"]["tests"][0]["weight"],
                1, "L'attribut weight n'a pas la bonne valeur par défaut")

    def test_test_weight_invalid(self):
        self.ht.write("""<?xml version="1.0"?>
        <templates>
        <template name="testtemplate">
            <test name="TestTest" weight="invalid">
                <arg name="TestArg1">TestValue1</arg>
                <arg name="TestArg2">TestValue2</arg>
            </test>
        </template>
        </templates>""")
        self.ht.close()
        self.assertRaises(ParsingError, conf.hosttemplatefactory.load_templates)

    def test_group(self):
        self.ht.write("""<?xml version="1.0"?>
                <templates>
                <template name="test">
                    <group>/Test group</group>
                </template>
                </templates>""")
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        assert "/Test group" in conf.hosttemplatefactory.templates["test"]["groups"], \
               "The \"group\" tag is not properly parsed"

    def test_group_whitespace(self):
        self.ht.write("""<?xml version="1.0"?>
                <templates>
                <template name="test">
                    <group> /Test group </group>
                </template>
                </templates>""")
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        assert "/Test group" in conf.hosttemplatefactory.templates["test"]["groups"], \
               "The \"group\" tag parsing does not strip whitespaces"

    def test_parent(self):
        self.ht.write("""<?xml version="1.0"?>
            <templates>
                <template name="test1">
                </template>
                <template name="test2">
                    <parent>test1</parent>
                </template>
            </templates>""")
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        assert "test1" in conf.hosttemplatefactory.templates["test2"]["parent"], \
               "The \"parent\" tag is not properly parsed"

    def test_parent_whitespace(self):
        self.ht.write("""<?xml version="1.0"?>
            <templates>
                <template name="test1">
                </template>
                <template name="test2">
                    <parent> test1 </parent>
                </template>
            </templates>""")
        self.ht.close()
        try:
            conf.hosttemplatefactory.load_templates()
        except KeyError:
            self.fail("The \"parent\" tag parsing does not strip whitespaces")
        assert "test1" in conf.hosttemplatefactory.templates["test2"]["parent"], \
               "The \"parent\" tag parsing does not strip whitespaces"

    def test_template_weight(self):
        self.ht.write("""<?xml version="1.0"?>
        <templates>
            <template name="test">
                <weight>42</weight>
            </template>
        </templates>""")
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        self.assert_("weight" in conf.hosttemplatefactory.templates["test"],
                     "L'attribut weight n'est pas chargé")
        self.assertEquals(conf.hosttemplatefactory.templates["test"]["weight"], 42,
                          "L'attribut weight n'a pas la bonne valeur")

    def test_template_weight_default(self):
        self.ht.write("""<?xml version="1.0"?>
        <templates>
            <template name="test">
            </template>
        </templates>""")
        self.ht.close()
        conf.hosttemplatefactory.load_templates()
        self.assert_("weight" in conf.hosttemplatefactory.templates["test"],
                     "L'attribut weight n'est pas réglé par défaut")
        self.assertEquals(conf.hosttemplatefactory.templates["test"]["weight"], 1,
                          "L'attribut weight n'a pas la bonne valeur par défaut")

    def test_template_weight_invalid(self):
        self.ht.write("""<?xml version="1.0"?>
        <templates>
            <template name="test">
                <weight>invalid</weight>
            </template>
        </templates>""")
        self.ht.close()
        self.assertRaises(ParsingError, conf.hosttemplatefactory.load_templates)


# vim:set expandtab tabstop=4 shiftwidth=4:
