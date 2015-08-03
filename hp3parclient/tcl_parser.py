# (c) Copyright 2015 Hewlett Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
""" TCL parser for 3PAR gettpdinterface and get output.

.. module: file_client
.. moduleauthor: Mark Sturdevant

:Author: Mark Sturdevant
:Description: TCL parser for 3PAR gettpdinterface and get output.
This module parses TCL strings and returns python structures.

"""

MAX_LEVELS = 10


class HP3ParTclParser(object):
    """The 3PAR TCL Parser."""

    @staticmethod
    def parse_tcl(tcl):

        token = ''
        result = []
        lists = [[]] * MAX_LEVELS

        level = -1

        for c in tcl:

            if c == '{':

                level += 1

                if level > MAX_LEVELS:
                    # For deeper nesting, just capture as string
                    token += c
                else:
                    token = ''
                    for l in range(0, level + 1):
                        lists[level] = []

            elif c == '}':

                if token != '' and level <= MAX_LEVELS:
                    lists[level].append(token)
                    token = ''

                if level > MAX_LEVELS:
                    # For deeper nesting, just capture as string
                    token += c
                elif level > 0:
                    lists[level - 1].append(lists[level])
                    lists[level] = []
                else:
                    result.append(lists[level])
                    lists[level] = []

                level -= 1

            elif c == ' ':
                if level > MAX_LEVELS:
                    # For deeper nesting, just capture as string
                    token += c
                elif token != '':
                    lists[level].append(token)
                    token = ''

            else:
                token += c

        return result
