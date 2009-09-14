# -*- coding: utf-8 -*-

class SSH(Test):
    """Check if the SSH service is up"""

    def add_test(self, host):
        """Arguments:
            host: the Host object to add the test to
        """
        host.add_external_sup_service("SSH", "check_ssh")


# vim:set expandtab tabstop=4 shiftwidth=4:
