# -*- coding: utf-8 -*-
#pylint: disable-msg=C0301,C0111,W0232,R0201,R0903,W0221

from vigilo.vigiconf.lib.confclasses.test import Test



class Metro(Test):
    """Set a threshold on metrology values"""

    def add_test(self, host, servicename, metroname, warn, crit, factor=1):
        """
        Set a threshold on metrology values
        @param servicename: the name of the Nagios service
        @type  servicename: C{str}
        @param metroname: the name of the metrology datasource to test
        @type  metroname: C{str}
        @param warn: the WARNING threshold.
        @type  warn: C{str}
        @param crit: the CRITICAL threshold.
        @type  crit: C{str}
        @param factor: the factor to use, if any
        @type  factor: C{int} or C{float}
        """
        host.add_metro_service(servicename, metroname, warn, crit, factor,
                               weight=self.weight,
                               warning_weight=self.warning_weight)


# vim:set expandtab tabstop=4 shiftwidth=4:
