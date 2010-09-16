################################################################################
#
# Copyright (C) 2007-2011 CS-SI
#
# This program is free software; you can redistribute it and/or modify
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
The local host Server instance
"""

from __future__ import absolute_import

import os

from vigilo.common.conf import settings

from vigilo.common.gettext import translate
_ = translate(__name__)

from ..server import Server, ServerError
from ..systemcommand import SystemCommandError

class ServerLocal(Server):
    """The local host"""

    def __init__(self, iName):
        # Superclass constructor
        Server.__init__(self, iName)

    def deployTar(self):
        tar = os.path.join(self.getBaseDir(), "%s.tar" % self.getName())
        cmd = self.createCommand(["vigiconf-local", "receive-conf", tar])
        try:
            cmd.execute()
        except SystemCommandError, e:
            raise ServerError(_("Can't deploy the tar archive for server "
                                "%s: %s") % (self.getName(), e.value))


# vim:set expandtab tabstop=4 shiftwidth=4:
