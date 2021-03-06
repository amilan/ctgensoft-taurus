#!/usr/bin/env python

#############################################################################
##
# This file is part of Taurus
##
# http://taurus-scada.org
##
# Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
##
# Taurus is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
##
# Taurus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
##
# You should have received a copy of the GNU Lesser General Public License
# along with Taurus.  If not, see <http://www.gnu.org/licenses/>.
##
#############################################################################

"""
"""

__docformat__ = "restructuredtext"

import os.path

from taurus.web.taurustornado import RequestHandler
from taurus.web.taurustornado import start, get_default_handlers


class MainHandler(RequestHandler):

    def get(self):
        self.render("machinestatus.html")


def main():
    local_path = os.path.dirname(__file__)
    static_path = os.path.join(local_path, 'static')
    handlers = [(r"/", MainHandler)] + get_default_handlers()

    start(handlers=handlers, static_path=static_path, debug=True)

if __name__ == "__main__":
    main()
