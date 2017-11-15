# -*- coding: utf-8 -*-
#pylint: disable-msg=C0301,C0111,W0232,R0201,R0903,W0221
# Copyright (C) 2006-2018 CS-SI
# License: GNU GPL v2 <http://www.gnu.org/licenses/gpl-2.0.html>

import re # for the detect_snmp function
import string
from vigilo.vigiconf.lib.confclasses.test import Test
from vigilo.vigiconf.lib.exceptions import ParsingError
from vigilo.common.gettext import translate
_ = translate(__name__)


class Interface(Test):
    """Check the status of an interface, and graph its throughput"""

    oids = [".1.3.6.1.2.1.25.1.6.0"]

    def add_test(self, label, ifname, max=None,
                 errors=True, staticindex=False, warn=None, crit=None,
                 counter32=False, teststate=True, admin="i", dormant="c" ):
        """
        The parameters L{warn} and L{crit} must be tuples in the form of
        strings separated by commas, for example: C{max_in,max_out} (in
        bits/s).

        If warn and crit contain 4 or 6 values, the next values will be applied
        in order to Discards and Errors if they are not None.
        Please note that sub-interfaces (VLANs) do not support SNMP queries
        for the discard and error counters.

        @param label: Label to display
        @type  label: C{str}
        @param ifname: SNMP name for the interface
        @type  ifname: C{str}
        @param max: the maximum bandwidth available through this interface, in
            bits/s
        @type  max: C{int}
        @param errors: create a graph for interface errors
        @type  errors: C{bool}
        @param staticindex: consider the ifname as the static SNMP index instead
            of the interface name. It's not recommanded, but it can be
            necessary as some OS (Windows among others) assign the same name to
            different interfaces.
        @type  staticindex: C{bool}
        @param warn: WARNING threshold. See description for the format.
        @type  warn: C{list}
        @param crit: CRITICAL threshold. See description for the format.
        @type  crit: C{list}
        @param counter32: Query the 32-bit counters instead of the 64-bit ones
            for this interface.
        @type  counter32: C{bool}
        @param teststate: Used to deactivate the interface state control. (When
            you only need statistics.)
        @type  teststate: C{bool}
        @param admin: Indique l'état à retourner pour une interface
            marquée comme "désactivée par l'administrateur". Les valeurs
            possibles sont "i" (ignorer / l'interface est vue comme étant
            dans l'état "OK"), "w" (l'interface est vue comme étant dans
            l'état "WARNING") ou bien "c" (l'interface est vue comme étant
            dans l'état "CRITICAL"). La valeur par défaut est "i".
        @type  admin: C{str}
        @param dormant: Indique l'état à retourner pour une interface
            marquée comme "dormante". Les valeurs possibles sont "i"
            (ignorer / l'interface est vue comme étant dans l'état "OK"),
            "w" (l'interface est vue comme étant dans l'état "WARNING")
            ou bien "c" (l'interface est vue comme étant dans l'état
            "CRITICAL"). La valeur par défaut est "c".
        @type  dormant: C{str}
        """
        errors = self.as_bool(errors)
        staticindex = self.as_bool(staticindex)
        counter32 = self.as_bool(counter32)
        teststate = self.as_bool(teststate)
        DHCIf = self.host.get_attribute("DisableHighCapacityInterface", False)
        if DHCIf is None:
            DHCIf = True
        DHCIf = self.as_bool(DHCIf)


        snmp_oids = {
            # using by default High Capacity (64Bits) COUNTER for in and out
            # http://www.ietf.org/rfc/rfc2233.txt
                "in": ".1.3.6.1.2.1.31.1.1.1.6",
                "out": ".1.3.6.1.2.1.31.1.1.1.10",
                "inDisc": ".1.3.6.1.2.1.2.2.1.13",
                "outDisc": ".1.3.6.1.2.1.2.2.1.19",
                "inErrs": ".1.3.6.1.2.1.2.2.1.14",
                "outErrs": ".1.3.6.1.2.1.2.2.1.20",
                }
        snmp_labels = {
                "in": "Input",
                "out": "Output",
                "inDisc": "Input discards",
                "outDisc": "Output discards",
                "inErrs": "Input errors",
                "outErrs": "Output errors",
                }

        special_states = ('i', 'w', 'c')

        if admin not in special_states:
            raise ParsingError(_('Invalid value "%(value)s" for %(param)s. '
                                 'Expected one of: %(candidates)s.') % {
                                     'value': admin,
                                     'param': 'admin',
                                     'candidates': ', '.join(special_states),
                                })

        if dormant not in special_states:
            raise ParsingError(_('Invalid value "%(value)s" for %(param)s. '
                                 'Expected one of: %(candidates)s.') % {
                                     'value': dormant,
                                     'param': 'dormant',
                                     'candidates': ', '.join(special_states),
                                })

        if DHCIf or counter32 :
            # using Low Capacity (32Bits) COUNTER for in and out
            snmp_oids["in"]  = ".1.3.6.1.2.1.2.2.1.10"
            snmp_oids["out"] = ".1.3.6.1.2.1.2.2.1.16"

        if staticindex:
            collector_function = "staticIfOperStatus"
            for snmpname, snmpoid in snmp_oids.iteritems():
                self.add_collector_metro("%s%s" % (snmpname, label),
                                         "directValue", [],
                                         [ "GET/%s.%s" % (snmpoid, ifname) ],
                                         "COUNTER", snmp_labels[snmpname],
                                         max_value=max)
        else:
            collector_function = "ifOperStatus"
            for snmpname, snmpoid in snmp_oids.iteritems():
                self.add_collector_metro("%s%s" % (snmpname, label),
                                         "m_table", [ifname],
                                         [ "WALK/%s" % snmpoid,
                                           "WALK/.1.3.6.1.2.1.2.2.1.2"],
                                         "COUNTER", snmp_labels[snmpname],
                                         max_value=max)

        if teststate is True:
            self.add_collector_service("Interface %s" % label, collector_function,
                [ifname, label, admin, dormant],
                ["WALK/.1.3.6.1.2.1.2.2.1.2", "WALK/.1.3.6.1.2.1.2.2.1.7",
                 "WALK/.1.3.6.1.2.1.2.2.1.8", "WALK/.1.3.6.1.2.1.31.1.1.1.18"])

        self.add_graph("Traffic %s" % label, ["in%s" % label, "out%s" % label],
                    "area-line", "b/s", group="Network interfaces",
                    factors={"in%s" % label: 8, "out%s" % label: 8, },)
        if errors:
            self.add_graph("Errors %s" % label,
                    [ "inErrs%s"%label, "outErrs%s"%label,
                      "inDisc%s"%label, "outDisc%s"%label ],
                    "lines", "packets/s", group="Network interfaces")

        # Supervision service
        if warn and crit:
            if warn[0] and crit[0]:
                self.add_metro_service("Traffic in %s"%label, "in"+label,
                                       warn[0], crit[0], 8)
            if warn[1] and crit[1]:
                self.add_metro_service("Traffic out %s"%label, "out"+label,
                                       warn[1], crit[1], 8)

            if len(warn) >= 4 and len(crit) >= 4:
                if warn[2] and crit[2]:
                    self.add_metro_service("Discards in %s"%label, "inDisc"+label,
                                           warn[2], crit[2], 8)
                if warn[3] and crit[3]:
                    self.add_metro_service("Discards out %s"%label, "outDisc"+label,
                                           warn[3], crit[3], 8)

                if len(warn) == 6 and len(crit) == 6 and errors:
                    if warn[4] and crit[4]:
                        self.add_metro_service("Errors in %s"%label, "inErrs"+label,
                                               warn[4], crit[4], 8)
                    if warn[5] and crit[5]:
                        self.add_metro_service("Errors out %s"%label, "outErrs"+label,
                                               warn[5], crit[5], 8)


    @classmethod
    def detect_snmp(cls, oids):
        """Detection method, see the documentation in the main Test class"""
        # Find the SNMP ids of interfaces with the right type. Types are in the
        # OID IF-MIB::ifType section
        intfids = []
        for oid in oids.keys():
            # Search IF-MIB::ifType
            if not oid.startswith(".1.3.6.1.2.1.2.2.1.3."):
                continue
            # Select the types
            # 6   => ethernetCsmacd
            # 7   => iso88023Csmacd
            # 22  => propPointToPointSerial
            # 23  => ppp
            # 53  => propVirtual
            # 135 => l2vlan
            # 136 => l3ipvlan
            allowed_types = [ "6", "7", "22", "23", "53", "135", "136" ]
            if oids[oid] not in allowed_types:
                continue
            # Extract the SNMP id
            intfids.append(oid.split(".")[-1])
        tests = []
        alphanum = string.letters + string.digits
        for intfid in intfids:
            # SNMP name: use IF-MIB::ifDescr and sanitize it
            ifname = oids[ ".1.3.6.1.2.1.2.2.1.2."+intfid ]
            ifname = re.sub("; .*", "; .*", ifname)
            if ifname == "lo": # Don't monitor the loopback
                continue
            # label: start with ifname and sanitize
            label = ifname
            label = re.sub("; .*", "", label)
            label = label.strip()
            label = label.replace("GigabitEthernet", "GE")
            label = label.replace("FastEthernet", "FE")

            # Protection contre les accents et
            # autres caractères spéciaux (#882).
            ifpattern = []
            ifname = ifname.decode('ascii', 'replace'
                            ).encode('ascii', 'replace')
            for c in ifname:
                # Les caractères > 127 sont remplacés par un '?'.
                if c == '?':
                    ifpattern.append('.')
                elif c in alphanum:
                    ifpattern.append(c)
                # Les autres caractères non-alphanumériques sont échappés.
                else:
                    ifpattern.append('\\' + c)
            ifname = ''.join(ifpattern)

            try:
                label.decode("ascii")
            except UnicodeDecodeError:
                # On essaye utf8 et latin1, sinon on remplace par des "?".
                try:
                    label = label.decode("utf8")
                except UnicodeDecodeError:
                    try:
                        label = label.decode("iso8859-1")
                    except UnicodeDecodeError:
                        label = label.decode("ascii", "replace")
            tests.append({"label": label, "ifname": ifname})
        return tests


    @classmethod
    def detect_attribute_snmp(cls, oids):
        """Detection method for the host attribute used in this test.
        See the documentation in the main Test class for details"""
        # Search if HighCapacity Counter must be disabled
        for oid in oids.keys():
            if oid.startswith(".1.3.6.1.2.1.31.1.1.1.6."):
                return None
        return {"DisableHighCapacityInterface": "yes"}


# vim:set expandtab tabstop=4 shiftwidth=4:
