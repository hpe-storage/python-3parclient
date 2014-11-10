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

TOP_LIST = 0
SUB_LIST = 1
SUB_SUB_LIST = 2


class HP3ParTclParser(object):
    """The 3PAR TCL Parser."""

    @staticmethod
    def parse_tcl(tcl):

        token = ''
        result = []
        top_list = []
        sub_list = []
        sub_sub_list = []
        lists = [top_list, sub_list, sub_sub_list]

        level = -1

        for c in tcl:

            if c == '{':

                level += 1

                if level > SUB_SUB_LIST:
                    # For deeper nesting, just capture as string
                    token += c
                else:
                    token = ''

                if level <= SUB_SUB_LIST:
                    # Start new sub-sub-list
                    lists[SUB_SUB_LIST] = []

                if level <= SUB_LIST:
                    # Starting new sub-list
                    lists[SUB_LIST] = []

            elif c == '}':

                if token != '' and level <= SUB_SUB_LIST:
                    lists[level].append(token)
                    token = ''

                if level > SUB_SUB_LIST:
                    # For deeper nesting, just capture as string
                    token += c
                elif level == SUB_SUB_LIST:
                    # End sub-sub-list.  Append it to parent.
                    lists[SUB_LIST].append(lists[SUB_SUB_LIST])
                    lists[SUB_SUB_LIST] = []
                elif level == SUB_LIST:
                    # End sub-list.  Append it to parent.
                    lists[TOP_LIST].append(lists[SUB_LIST])
                    lists[SUB_LIST] = []
                elif level == TOP_LIST:
                    # End a top-list.
                    result.append(lists[TOP_LIST])
                    lists[TOP_LIST] = []

                level -= 1

            elif c == ' ':
                if level > SUB_SUB_LIST:
                    # For deeper nesting, just capture as string
                    token += c
                elif token != '':
                    lists[level].append(token)
                    token = ''

            else:
                token += c

        return result
