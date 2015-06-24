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
""" HP3PAR File Persona Client

.. module: file_client
.. moduleauthor: Mark Sturdevant

:Author: Mark Sturdevant
:Description: Client for 3PAR File Persona.
    This module provides a client for File Persona functionality.
    The File Persona client requires 3PAR InForm 3.2.1 (MU3) with File Persona
    capability.  This client extends the regular 3PAR client.

"""

import logging
from functools import wraps

from hp3parclient import client
from hp3parclient import tcl_parser

TCL = tcl_parser.HP3ParTclParser()
LOG = logging.getLogger(__name__)

# Commands that require -f (non-interactive) flag register with _force_me
FORCE_ME = {}
# Commands that require -d (get details) flag register with _get_details
GET_DETAILS = {}
# Commands that require the protocol arg before any option flags register here
PROTOCOL_FIRST = {}


class HP3ParFilePersonaClient(client.HP3ParClient):

    """ The 3PAR File Persona Client.

    The File Persona client requires 3PAR InForm 3.2.1 (MU3) with File Persona
    capability

    :param api_url: The url to the WSAPI service on 3PAR
                    ie. http://<3par server>:8080/api/v1
    :type api_url: str

    """

    # File Persona minimum WSAPI overrides minimum for non-File Persona.
    HP3PAR_WS_MIN_BUILD_VERSION = 30201256
    HP3PAR_WS_MIN_BUILD_VERSION_DESC = '3.2.1 (MU3)'

    def __init__(self, api_url, secure=False):
        super(self.__class__, self).__init__(api_url, secure=secure)
        self.interfaces = None

    @staticmethod
    def _build_command(command, *args, **kwargs):
        """Build a SSH/CLI command based on command + args + kwargs.

        A built cmd will look like:  command [OPTIONS] [SPECIFIERS]
        It is returned as an array of strings to be passed to ssh.run.

        command can be a string or list of strings.  If it is a string, it will
        be split().  This allows commands with flags like 'doit -v' to work.
        Passing in ['doit','-v'] has the same result.

        Options are taken from kwargs.  The CLI option will be a hyphen
        followed by the kwarg key.  E.g., -key.

        If the value is None, then the option is skipped.

        If the value is a boolean, then False options are ignored and True
        options are set as flags.  E.g., '-debug' with no value after it.
        Note: a _quoted_ 'true' or 'false' is treated as a string (below) and
        this is important to allow so that we can also do '-enabled true'.

        Options with non-boolean values will be used like '-key value'
        (of course returned as '-key', 'value' in the array).

        Since embedded spaces in a value are not allowed by the injection
        checker without  quoting (and quoting inside strings is not natural)
        kwargs with key named 'comment' will automatically have their value
        quoted.

        :returns: list of strings
        """

        # Command is a string or a list like ['doit','-f']
        if isinstance(command, str):
            # If a string, split it into a list.
            cmd = command.split()
        else:
            cmd = command

        # Some commands require the protocol {smb|nfs} before the option flags.
        # To use this abnormal pattern those methods register in
        # PROTOCOL_FIRST.
        if cmd[0] in PROTOCOL_FIRST:
            # Add the protocol (args[1]) to the command and eat it.
            protocol = args[1]
            cmd.append(protocol)
            new_args = [args[0]]
            new_args.extend(args[2:])
            args = new_args

        # Some commands require the -f flag so that they are non-interactive.
        # Those methods register in FORCE_ME.
        if cmd[0] in FORCE_ME:
            cmd.append('-f')
            # -f is forced to True (we are non-interactive).
            # If we find it in a kwarg, eat it.
            force = kwargs.pop('f', True)
            if not force:
                # If anyone thought they could override this. Log it.
                LOG.info(
                    "Ignoring f=False. Always non-interactive for %s." %
                    cmd[0])

        # Some commands require the -d flag so that we get details (because
        # our parser might expect them).
        # Those methods register in GET_DETAILS.
        if cmd[0] in GET_DETAILS:
            cmd.append('-d')
            # 'd' is in signature for completeness, but is forced to True
            # Eat it.
            details = kwargs.pop('d', True)
            if not details:
                # If anyone thought they could override this. Log it.
                LOG.info(
                    "Ignoring d=False. Always getting details for %s." %
                    cmd[0])

        # Add the options
        if len(kwargs) > 0:
            for k, v in list(kwargs.items()):
                if isinstance(v, bool):
                    # Boolean, just add a flag if true. No value.
                    if v:
                        cmd.append('-%s' % k)
                elif v:
                    # Non-Boolean.  Add -opt value, if not None.
                    cmd.append("-%s" % k)
                    if k == 'comment':  # Quoting needed for comments (spaces)
                        cmd.append('"%s"' % v)
                    else:
                        cmd.append(v)

        # Add the specifiers
        if len(args) > 1:
            cmd.extend(args[1:])
        return cmd

    @staticmethod
    def _build_command_and_run_with_ssh(cmd, *args, **kwargs):
        """Build CLI command from cmd, args, kwargs and run it with ssh."""
        client = args[0]  # first arg is the client itself
        command = HP3ParFilePersonaClient._build_command(cmd, *args, **kwargs)
        client.ssh.open()
        return client.ssh.run(command, multi_line_stripper=True)

    def _run_with_cli(func):
        """Decorator to build command from method signature and run SSH/CLI.

        The command is built from the method name, args and kwargs.
        The results of the CLI command are returned.  The actual results of the
        original method are not used, but the method will be ran so that
        prints, logging can be used.

        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            return HP3ParFilePersonaClient._build_command_and_run_with_ssh(
                func.__name__, *args, **kwargs)
        return wrapper

    def _get_details(func):
        """Decorator for a command/method that needs the -d flag.

        Our parser might only recognize data with details, so always set d=True
        in these cases.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            GET_DETAILS[func.__name__] = True
            func(*args, **kwargs)
        return wrapper

    def _force_me(func):
        """Decorator for a command/method that needs the -f flag.

        When used, this decorator should be below the @_run_with_cli decorator.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            FORCE_ME[func.__name__] = True
            func(*args, **kwargs)
        return wrapper

    def _protocol_first(func):
        """Decorator for a command/method that needs protocol arg before flags.

        When used, this decorator should be below the @_run_with_cli decorator.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            PROTOCOL_FIRST[func.__name__] = True
            func(*args, **kwargs)
        return wrapper

    def _set_key_value(self, dictionary, key, value):
        """Set value for key in dictionary with some special key treatment."""
        if key == 'comment' and isinstance(value, list):
            # Special treatment for comments. They are the one thing that
            # we don't want ['split', 'into', 'a', 'nice', 'list'].
            # Put them back together.
            dictionary[key] = ' '.join(value)
        elif key == 'vfsip' and value:
            # Expand the sub-fsips like in getfsip.
            interface = self.gettpdinterface()['getfsipInd']
            dictionary[key] = self._create_member(interface, value[0])
        else:
            dictionary[key] = value

    def _wrap_tpd_interface(func):
        """Take gettpdinterface results and set interfaces."""

        def get_interface_keys(interface):
            keys = []
            key_pos_pairs = interface[1]
            for pair in key_pos_pairs:
                key = pair[0]
                split_key = key.split(',')
                if len(split_key) == 1:
                    keys.append(key)
                else:
                    current_key = keys[-1]
                    sub_key = split_key[1]
                    if isinstance(current_key, str):
                        # If this is current_key,sub_key, then
                        # make current_key (current_key, [sub_key])
                        current_key = (current_key, [sub_key])
                    else:
                        # Already (current_key, [sub_key,...]
                        # Append the new sub_key to list.
                        current_key[1].append(sub_key)
                    keys[-1] = current_key
            return keys

        @wraps(func)
        def wrapper(*args, **kwargs):
            client = args[0]  # first arg is the client itself

            cached = client.interfaces
            if cached is not None:
                return cached

            result = func(*args, **kwargs)

            # Since there are many, we ignore interfaces not in this list.
            # This reduces memory use (and also allows our fake server to work)
            supported_commands = [
                'getfsharenfsInd',
                'getfsharesmbInd',
                'getfsipInd',
                'getfsnapInd',
                'getfsnapcleanInd',
                'getfsquotaInd',
                'getfspoolInd',
                'getfssystemInd',
                'getfstoreInd',
                'getvfsInd',
            ]

            tpd_interfaces = TCL.parse_tcl(result[0])

            interfaces = {}
            for interface in tpd_interfaces:
                interface_name = interface[0]
                if interface_name in supported_commands:
                    interfaces[interface_name] = get_interface_keys(interface)

            # Cache the interfaces
            client.interfaces = interfaces
            return interfaces
        return wrapper

    def _parse_members(self, keys, data):
        members = []
        if data:
            if len(keys) > 1 and isinstance(data[0], list):
                members = []
                # list of members (list of lists)
                for values in data:
                    member = dict(list(zip(keys, values)))
                    members.append(member)
            else:
                # 1 member (list of values)
                members = dict(list(zip(keys, data)))
        return members

    def _create_member(self, interface, values):
        member = {}
        for index, item in enumerate(values):
            if isinstance(interface[index], str):
                key = interface[index]
                self._set_key_value(member, key, item)
            else:
                header, keys = interface[index]
                sub_list = self._parse_members(keys, item)
                member[header] = sub_list
        return member

    def _wrap_tcl(func):
        """Turn TCL output into Python dicts."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            client = args[0]  # first arg is the client itself

            command = func.__name__
            result = func(*args, **kwargs)

            if not result:
                return {
                    'message': None,
                    'total': 0,
                    'members': []
                }

            # Combine output lines into one string
            result_str = ''.join(result)

            # Non-TCL output is just a message (probably an error message)
            if not result_str.startswith('{'):
                return {
                    'message': result_str,
                    'total': 0,
                    'members': []
                }

            single = False
            # Get interface for command (some special cases)
            if command == 'getfpg':
                # Interface uses old "fspool" name
                interface_id = 'getfspoolInd'
            elif command == 'getfs':
                # Get the whole thing with getfssystemInd
                single = True
                interface_id = 'getfssystemInd'
            elif command == 'getfshare' and args[1] == 'nfs':
                interface_id = 'getfsharenfsInd'
            elif command == 'getfshare' and args[1] == 'smb':
                interface_id = 'getfsharesmbInd'
            else:
                # Normal case should be cmd + 'Ind'
                interface_id = '%sInd' % command

            interface = client.gettpdinterface()[interface_id]

            parsed_result = TCL.parse_tcl(result_str)

            # getfsip has extra level of nesting.
            if command == 'getfsip':
                parsed_result = parsed_result[0]

            # getfsnapclean added a special 'not running' message
            # Filter out that garbage.
            if command == 'getfsnapclean':
                not_running = ['No', 'reclamation', 'task', 'running']
                parsed_result = [x for x in parsed_result if x[0:4] !=
                                 not_running]

            if single:
                # Single member (need to add to list)
                members = [client._create_member(interface, parsed_result)]
            else:
                members = []
                for values in parsed_result:
                    members.append(client._create_member(interface, values))
            return {'members': members, 'total': len(members), 'message': None}

        return wrapper

    @_wrap_tpd_interface
    @_run_with_cli
    def gettpdinterface(self):
        """Get and parse TPD interfaces (and set for re-use).

        The output is filtered to only include interfaces used by
        this client.

        :return: Dictionary of TPD interfaces
        """

    @_wrap_tcl
    @_run_with_cli
    def getfs(self):
        """Show information on File Services cluster.

        The getfs command displays information on File Services nodes.

        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of FS settings.
            }

        """

    @_run_with_cli
    def createfpg(self, cpgname, fpgname, size,
                  comment=None, node=None,
                  full=False, wait=False):
        """Create a file provisioning group.

        The createfpg command creates a file provisioning group of the given
        name and size within the specified cpg.

        For this command MB = 1048576 bytes, GB = 1024MB, and TB = 1024GB.

        :param cpgname: The CPG where the VVs associated with the file
                        provisioning group will be created
        :param fpgname: The name of the file provisioning group to be created
        :param size: The size of the file provisioning group to be created.
                     The specified size must be between 1T and 32T.
                     A suffix (with no whitespace before the suffix) will
                     modify the units to GB (g or G suffix) or TB (t or T
                     suffix).
        :param comment: Specifies the textual description of the file
                        provisioning group.
        :param node: Bind the created file provisioning group to the specified
                     node.
        :param full: Create the file provisioning group using fully
                     provisioned volumes.
        :param wait: Wait until the associated task is completed before
                     proceeding.  This option will produce verbose task
                     information.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    def growfpg(self, fpgname, size):
        """Grow a file provisioning group.

        The growfpg command grows a file provisioning group of the given name
        by the size specified, within the CPG associated with the base file
        provisioning group.

        For each grow undertaken, at least one additional VV of name
        <fpgname>.n is created.

        :param fpgname: The name of the filesystem to be grown.
        :param size: The size of the filesystem to be grown.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_wrap_tcl
    @_run_with_cli
    def getfpg(self, *fpgs):
        """Show file provisioning group information

        The getfpg command displays information on file provisioning groups

        :param fpgs: Limit output to the specified file provisioning group.
        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of FPGs
            }

        """

    @_run_with_cli
    @_force_me
    def setfpg(self, fpgname,
               comment=None, rmcomment=False, activate=False,
               deactivate=False, primarynode=None, failover=False,
               forced=False):
        """Modify the properties of a File Provisioning Group.

        The setfpg command allows the user to enable and disable various
        properties associated with a File Provisioning Group.

        Access to all domains is required to run this command.

        The -primarynode and -failover options are mutually exclusive.

        When assigning primary nodes, the secondary node will be implicit
        as a couplet pair [0,1] [2,3] [4,5] [6,7].  This action will fail
        if the graceful failover is not possible.

        The -failover and -primarynode options will result in temporary
        unavailability of the Virtual File Servers associated with the File
        Provisioning Group being migrated, and also the unavailability of any
        associated shares.  An implicit -deactivate and -activate process is
        undertaken during a migration to the alternate node.

        :param fpgname: The name of the file provisioning group to be modified.
        :param comment: Specifies any addition textual information.
        :param rmcomment: Clears the comment string.
        :param activate: Makes the File Provisioning Group available.
        :param deactivate: Makes the File Provisioning Group unavailable.
        :param primarynode: Specifies the primary node to which the File
                            Provisioning Group will be assigned.
                            Appropriate <nodeid> values are defined as those
                            on which file services has been enabled.
        :param failover: Specifies that the File Provisioning Group should
                         be failed over to its alternate node.
                         If it has previously failed over to the secondary,
                         this will cause it to fail back to the primary node.
                         Will fail if a graceful failover is not possible.
        :param forced: In the event of failure to failover, this will attempt
                       a forced failover.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def removefpg(self, *fpgname, **kwargs):
        r"""Remove a file provisioning group

        The removefpg command removes a file provisioning group and its
        underlying components from the system.

        It is necessary to remove any shares on the file provisioning group
        before removing the file provisioning group itself.

        :param fpgname: fpgname is the name of the file provisioning group(s)
                        to be removed. This specifier can be repeated to
                        remove multiple file provisioning groups.  When used
                        with pat=True, specifies a glob-style pattern.
                        This specifier can be repeated to remove multiple
                        file provisioning groups.
        :param \**kwargs: See below.
        :kwargs:
            * **forget** -- Removes the specified file provisioning group
              which is involved in Remote DR, keeping the virtual
              volume intact.
            * **wait** -- Wait until the associated task is completed before
              proceeding. This option will produce verbose task
              information.
            * **pat** -- The fpgname parameter is a glob-style pattern.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    def createvfs(self, ipaddr, subnet, vfsname,
                  nocert=False, certfile=None, certdata=None,
                  comment=None, bgrace=None, igrace=None,
                  fpg=None,
                  cpg=None, size=None, node=None,
                  vlan=None,
                  wait=False):
        """Create a Virtual File Server.

        createvfs creates a Virtual File Server. It can optionally create the
        File Provisioning Group to which the VFS will belong.

        If an fpg is created, it will be given the same name as the VFS.
        Both names must be available for creation for the command to succeed.

        Either -fpg or the parameters to create a File Provisioning Group must
        be specified in order to create a VFS.

        This command will spawn a task and return the taskid.

        Grace times are specified in minutes.

        Certificates must be in PEM format, containing both public and
        private keys.

        Only one of the following certificate options can be specified:
        nocert, certfile, certdata.

        :param ipaddr: The IP address to which the VFS should be assigned
        :param subnet: The subnet for the IP Address.
        :param vfsname: The name of the VFS to be created.
        :param nocert: Do not create a self signed certificate associated with
                       the VFS.
        :param certfile: Use the certificate data contained in this file.
        :param certdata: Use the certificate data contained in this string.
        :param comment: Specifies any additional textual information.
        :param bgrace: The block grace time in minutes for quotas within the
                       VFS.
        :param igrace: The inode grace time in minutes for quotas within the
                       VFS.
        :param fpg: The name of the File Provisioning Group in which the VFS
                    should be created.
        :param cpg: The CPG in which the File Provisioning Group should be
                    created.
        :param size: The size of the File Provisioning Group to be created.
        :param node: The node to which the File Provisioning Group should be
                     assigned.
        :param vlan: The VLAN ID associated with the VFSIP.
        :param wait: Wait until the associated task is completed before
                     proceeding. This option will produce verbose task
                     information.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_wrap_tcl
    @_run_with_cli
    @_get_details
    def getvfs(self, fpg=None, vfs=None):
        """Display Virtual File Server information.

        The getvfs command displays information on Virtual File Servers.

        VFS name is not globally unique, and the same VFS name may be in use
        in multiple File Provisioning Groups.

        If no filter options are provided the system will traverse all
        File Provisioning Groups and display all associated VFSs.

        :param fpg: Limit the display to VFSs contained within the
                    File Provisioning Group.
        :param vfs: Limit the display to the specified VFS name.
        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of VFSs.
            }

        """

    @_run_with_cli
    def setvfs(self, vfs, fpg=None,
               certfile=None, certdata=None, certgen=False, rmcert=None,
               comment=None, bgrace=None, igrace=None):
        """Modify a Virtual File Server.

        Allows modification of the specified Virtual File Server

        Only one of the following certificate options can be specified:
        certfile, certdata, certgen, rmcert.

        Certificates must be in PEM format, containing both public and
        private keys.

        Grace times are specified in minutes.

        :param vfs: The name of the VFS to be modified.
        :param fpg: The name of the File Provisioning Group to which the VFS
                    belongs.
        :param certfile: Use the certificate data contained in this file.
        :param certdata: Use the certificate data contained in this string.
        :param certgen: Generates and sets a certificate for the VFS.
        :param rmcert: Remove the named certificate from the VFS.
        :param comment: Specifies any additional textual information.
        :param bgrace: Specifies the block grace time for quotas within the
                       VFS.
        :param igrace: Specifies the inode grace time for quotas within the
                       VFS.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def removevfs(self, vfs, fpg=None):
        """Remove a Virtual File Server.

        The removevfs command removes a Virtual File Server and its underlying
        components from the system.

        :param vfs: The name of the VFS to be removed.
        :param fpg: fpg is the name of the File Provisioning Group containing
                    the VFS
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    def createfsip(self, ipaddr, subnet, vfs, vlantag=None, fpg=None):
        """Assigns an IP address to a Virtual File Server.

        :param ipaddr: Specifies the IP address to be assign to the Virtual
                       File Server.
        :param subnet: Specifies the subnet mask to be used.
        :param vfs: Specifies the Virtual File Server to which the IP
                    address will be assigned.
        :param vlantag: Specifies the VLAN Tag to be used.
        :param fpg: Specifies the file provisioning group in which the
                    Virtual File Server was created.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def setfsip(self, vfs, id, vlantag=None, ip=None, subnet=None, fpg=None):
        """Modifies the network config of a Virtual File Server.

        :param vfs: Specifies the Virtual File Server which is to have its
                    network config modified.
        :param id: Specifies the ID for the network config.
        :param vlantag: Specifies the VLAN Tag to be used.
        :param ip: Specifies the new IP address.
        :param subnet: Specifies the new subnet mask.
        :param fpg: Specifies the File Provisioning Group in which the
                    Virtual File Server was created.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_wrap_tcl
    @_run_with_cli
    def getfsip(self, vfs, fpg=None):
        """Shows the network config of a Virtual File Server.

        :param vfs: Specifies the Virtual File Server which is to have its
                    network config modified.
        :param fpg: Specifies the File Provisioning Group in which the Virtual
                    File Server was created.
        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of FSIPs.
            }

        """

    @_run_with_cli
    @_force_me
    def removefsip(self, vfs, id, fpg=None):
        """Removes the network config of a Virtual File Server.

        :param vfs: Specifies the Virtual File Server which is to have its
                    network config removed.
        :param id: Specifies the ID for the network config.
        :param fpg: Specifies the File Provisioning Group in which the Virtual
                    File Server was created.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    def createfsgroup(self, groupname, gid=None, memberlist=None):
        """Create a local group account associated with file services.

        The -gid option can have any value between 1000 and 65535.

        To access an SMB share, specify the group as
        "LOCAL_CLUSTER\<groupname>".

        :param groupname: Specifies the local group name using up to 31
                          characters. Valid characters are alphanumeric
                          characters, periods, dashes (except first character),
                          and underscores.
        :param gid: Specifies the group ID to be used.
        :param memberlist: User members of the group.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def setfsgroup(self, groupname, memberlist=None):
        """Modify a local group account associated with file services.

        memberlist specifies user members of the group. It is a set of comma
        separated strings (memberlist='<list>').

        If <list> has a prefix (for example, +user1):

        \+  add <list> to the existing user list. Users in <list> must not be
        in the existing list.

        \-  remove <list> from the existing list. Users in <list> must be
        already in the existing list.

        If specified, the prefix will be applied to the entire list.
        If <list> has no prefix, <list> will be used as the new
        user list.

        :param groupname: Specifies the local group name using up to 31
                          characters. Valid characters are alphanumeric
                          characters, periods, dashes (except first
                          character), and underscores.
        :param memberlist: Specifies user members of the group.
                           It is a set of comma separated strings.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def removefsgroup(self, groupname):
        """Remove a local group account associated with file services.


        :param groupname: Specifies the local group name using up to 31
                          characters. Valid characters are alphanumeric
                          characters, periods, dashes (except first
                          character), and underscores.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    def createfsuser(self, username, passwd='default', primarygroup=None,
                     enable=None, uid=None, grplist=None):
        """Create a local user account associated with file services.

        If not specified -uid will be given a default value.

        The -uid option can have any value between 1000 and 65535.

        If the -enabled option is not supplied the user will be
        enabled by default.  Valid values are strings 'false' or 'true'
        (default).  These values are strings -- not Python booleans.

        To access an SMB share, specify the user as "LOCAL_CLUSTER\<username>".

        :param username: Specifies the local user name using up to 31
                         characters. Valid characters are alphanumeric
                         characters, periods, dashes (except first
                         character), and underscores.
        :param passwd: Specifies the user's password.
        :param primarygroup: Specifies the user's primary group.
        :param enable: Specifies the user is enabled or disabled on creation.
                       Valid values are strings 'false' or 'true' (default).
                       These values are strings -- not Python booleans.
        :param uid: Specifies the user ID to be used.
        :param grplist: Specifies a list of additional groups the user is to be
                        a member.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def setfsuser(self, username, passwd=None, primarygroup=None,
                  enable=None, grplist=None):
        """Modify a local user account associated with file services.

        Valid values for enabled are strings 'false' or 'true' (or None).
        These values are strings -- not Python booleans.

        grplist specifies a list of additional groups which the user is to be a
        member. It is a set of comma separated strings (grplist='<list>').

        If <list> has a prefix (for example, +group1):

        \+   add <list> to the existing group list. Groups in <list>
        must not be in the existing list.

        \-   remove <list> from the existing list. Groups in <list>
        must be already in the existing list.

        If specified, the prefix will be applied to the entire list.
        If <list> has no prefix, <list> will be used as the new
        group list.

        :param username: Specifies the local user name using up to 31
                         characters. Valid characters are alphanumeric
                         characters, periods, dashes (except first
                         character), and underscores.
        :param passwd: Specifies the user's password.
        :param primarygroup: Specifies the user's primary group.
        :param enable: Specifies if the user is enabled or not.
        :param grplist: Specifies a list of additional groups which the user
                        is to be a member. It is a set of comma separated
                        strings.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def removefsuser(self, username):
        """Remove a local user account associated with file services.

        :param username: Specifies the local user name using up to 31
                         characters. Valid characters are alphanumeric
                         characters, periods, dashes (except first
                         character), and underscores.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    def createfstore(self, vfs, fstore, comment=None, fpg=None):
        """Create a file store.

        The createfstore command creates a new fstore with the specified name
        for the specified storage pool and the virtual file system.

        :param vfs: Specifies the name of the virtual file system.
        :param fstore: Specifies the name of the file store to be created.
        :param comment: Specifies the textual description of the fstore.
        :param fpg: Specifies the name of the file provisioning group.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_wrap_tcl
    @_run_with_cli
    def getfstore(self, fpg=None, vfs=None, fstore=None):
        """Display File Store information.

        The showfstore command displays information on the file stores.
        To specify VFS or fstore filters, the parent components must be
        specified.

        :param fpg: Limit the display to virtual file servers contained
                    within the file provisioning group.
        :param vfs: Limit the display to the specified virtual file server.
        :param fstore: Limit the display to the specified file store.
        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of fstores.
            }

        """

    @_run_with_cli
    def setfstore(self, vfs, fstore, comment=None, fpg=None):
        """Modify a File Store.

        :param vfs: The name of the containing Virtual File Server.
        :param fstore: The name of the fstore to be modified.
        :param comment: Specifies any addition textual information.
        :param fpg: The name of the parent File Provisioning Group.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def removefstore(self, vfs, fstore, fpg=None):
        """Remove a File Store

        The removefstore command removes a File store and its underlying
         components from the system

        :param vfs: The name of the containing Virtual File Server.
        :param fstore: The name of the fstore to be removed.
        :param fpg: The name of the parent File Provisioning Group.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_protocol_first
    @_force_me
    def createfshare(self, protocol, vfs, sharename,
                     fpg=None, fstore=None, sharedir=None, comment=None,
                     abe=None, allowip=None,
                     denyip=None, allowperm=None, denyperm=None, cache=None,
                     ca=None,
                     options=None, clientip=None, ssl=None, urlpath=None):
        """Create a file share.

        The createfshare command creates file shares for supported protocols.

        PROTOCOLS

        smb
            Creates an SMB file share.
        nfs
            Creates an NFS file share.
        obj
            Creates an Object file share.

        OPTIONS

        The following parameters are for all protocols:

            fpg <fpgname>
            fstore <fstore>
            sharedir <sharedir>
            comment <comment>

        The following options are specific to each subcommand:

        smb
            abe {true|false}
            allowip <iplist>
            denyip <iplist>
            allowperm <permlist>
            denyperm <permlist>
            cache {off|manual|optimized|auto}
            ca {true|false}

        nfs
            options <options>
            clientip <clientlist>

        obj
            ssl {true|false}
            urlpath <urlpath>

        The file provisioning group and its underneath virtual file server must
        be created before creating file shares.

        For SMB permissions, the same user cannot be specified with the same
        permission in both "allowperm" and "denyperm".

        To access an SMB share:
        for users configured locally, specify "LOCAL_CLUSTER\<user>",
        for users configured on Active Directory, specify "<domain>\<user>" or
        "<ad-netbios>\<user>",
        for users configured on the LDAP server, specify
        "<ldap-netbios>\<user>".

        For NFS shares, it is not allowed to create two shares which have
        identical clients (i.e. specified by -clientip) and share directory
        (i.e. specified by -sharedir). If you create NFS shares without
        specifying different -clientip and -sharedir options, the second
        "createfshare" will fail.

        To create Object share, the virtual file server specified by <vfs>
        must have an associated IP address.

        :param protocol: The protocol {'nfs'|'smb'|'obj'}
        :param vfs: The virtual file server under which the file store,
                    if it does not exist, and the share will be created.
        :param sharename: The share name to be created.
        :param fpg: Specifies the file provisioning group that <vfs> belongs.
            If this is not specified, the command will find out the file
            provisioning group based on the specified <vfs>. However, if <vfs>
            exists under multiple file provisioning groups, -fpg must be
            specified.
        :param fstore: Specifies the file store under which the share will be
             created. If this is not specified, the command uses the
             <sharename> as the file store name. The file store will be created
             if it does not exist.
        :param sharedir: Specifies the directory path to share. It can be a
             full path starting from "/", or a relative path under the file
             store. If this is not specified, the share created will be rooted
             at the file store. If option is specified, option -fstore must be
             specified.
        :param comment: Specifies any comments or additional information for
             the share. The comment can be up to 255 characters long.
             Unprintable characters are not allowed.
        :param abe: Access Based Enumeration. Specifies if users can see only
             the files and directories to which they have been allowed access
             on the shares. The default is 'false'.  Valid values are 'true',
             'false' or None.  The parameter is a Python string -- not a
             boolean.
        :param allowip: Specifies client IP addresses that are allowed access
             to the share. Use commas to separate the IP addresses. The default
             is "", which allows all IP addresses (i.e. empty means all are
             allowed).
        :param denyip: Specifies client IP addresses that are denied access to
             the share. Use commas to separate the IP addresses. The default is
             "", which denies none of IP addresses (i.e. empty means none is
             denied).
        :param allowperm: Specifies the permission that a user/group is allowed
             to access the share. <permlist> must be specified in the format
             of: "<user1>:<perm1>,<user2>:<perm2>,...". <user> can be a user or
             group name. <perm> must be "fullcontrol", "read", or "change".

             "Everyone" is a special user for all users and groups.

             If the user is configured locally using "createfsuser", use <user>
             to specify the user (for example, -allowperm user1:fullcontrol).

             If the user is configured on Active Directory, use "setfs ad"
             to join Active Directory domain with <domain> if it has not been
             done, and use "<domain>\\<user>" or "<ad-netbios>\\<user>"
             to specify the user (for example, -allowperm
             example.com\\aduser:fullcontrol). The <ad-netbios> can be found
             by running "showfs -ad".

             If the user is configured on the LDAP server, use "setfs ldap"
             to create LDAP configuration with <ldap-netbios> if it has not
             been done, and use "<ldap-netbios>\\<user>" to specify the user
             (for example, -allowperm ldaphost\\ldapuser:read).

             If not specified, no default permissions will be allowed for the
             new shares, which sets the same default as a Windows Server 2012
             R2 server would. This is to avoid a system administrator
             inadvertently allowing any non explicitly specified user to be
             able to access the SMB share.

        :param denyperm: Specifies the permission that a user/group is denied
             to access the share. <permlist> must be specified in the format
             of: "<user1>:<perm1>,<user2>:<perm2>,...". <user> can be a user or
             group name. <perm> must be "fullcontrol", "read", or "change".

             "Everyone" is a special user for all users and groups.

             If the user is configured locally using "createfsuser", use <user>
             to specify the user (for example, -denyperm user1:fullcontrol).

             If the user is configured on Active Directory, use "setfs ad"
             to join Active Directory domain with <domain> if it has not been
             done, and use "<domain>\\<user>" or "<ad-netbios>\\<user>"
             to specify the user (for example, -denyperm
             example.com\\aduser:fullcontrol). The <ad-netbios> can be found
             by running "showfs -ad".

             If the user is configured on the LDAP server, use "setfs ldap"
             to create LDAP configuration with <ldap-netbios> if it has not
             been done, and use "<ldap-netbios>\\<user>" to specify the user
             (for example, -denyperm ldaphost\\ldapuser:read).

        :param cache: Specifies client-side caching for offline files. Valid
             values are:
             "off": The client must not cache any files from this share. The
             share is configured to disallow caching.
             "manual": The client must allow only manual caching for the files
             open from this share.
             "optimized": The client may cache every file that it opens from
             this share. Also, the client may satisfy the file requests from
             its local cache. The share is configured to allow automatic
             caching of programs and documents.
             "auto": The client may cache every file that it opens from this
             share. The share is configured to allow automatic caching of
             documents.
             If this is not specified, the default is "manual".

        :param ca: Continuous Availability. Specifies if SMB3 continuous
             availability features should be enabled for this share. If not
             specified, the default is 'true'. Valid values are 'true',
             'false' or None. The parameter is a Python string -- not a
             boolean.

        :param options: Specifies options to use for the share to be created.
             Standard NFS export options except "no_subtree_check" are
             supported. Do not enter option "fsid", which is provided. If not
             specified, the following options will be automatically set:
             sync, auth_nlm, wdelay, sec=sys, no_all_squash, crossmnt, secure,
             subtree_check, hide, root_squash, ro.

             See linux exports(5) man page for detailed information.

        :param clientip: Specifies the clients that can access the share.
             The NFS client can be specified by the name (for example,
             sys1.hp.com), the name with a wildcard (for example, *.hp.com), or
             by its IP address. Use comma to separate the IP addresses. If this
             is not specified, the default is "*".
        :param ssl: Specifies if SSL is enabled. The default is false.
        :param urlpath: Specifies the URL that clients will use to access the
             share. If this is not specified, the command uses <sharename> as
             <urlpath>.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_protocol_first
    def setfshare(self, protocol, vfs, sharename,
                  fpg=None, fstore=None, comment=None,
                  abe=None, allowip=None,
                  denyip=None, allowperm=None, denyperm=None, cache=None,
                  ca=None,
                  options=None, clientip=None,
                  ssl=None):
        """Set/modify file share properties.

        The setfshare command modifies file share properties for supported
        protocols.

        For setting SMB permissions, the same user cannot be specified with
        the same permission in both "allowperm" and "denyperm".

        PROTOCOLS

        smb
            Sets file share options for SMB.
        nfs
            Sets file share options for NFS.
        obj
            Sets file share options for Object.

        OPTIONS

        The following options are for all protocols:

            fpg <fpgname>
            fstore <fstore>
            comment <comment>

        The following options are specific to each protocol:

        smb
            -abe {true|false}
            -allowip [+|-]<iplist>
            -denyip [+|-]<iplist>
            -allowperm [+|-|=]<permlist>
            -denyperm [+|-|=]<permlist>
            -cache {off|manual|optimized|auto}
            -ca {true|false}

        nfs
            -options <options>
            -clientip [+|-]<iplist>

        obj
            -ssl {true|false}

        :param protocol: The protocol {'nfs'|'smb'|'obj'}
        :param vfs: Specifies the virtual file server that the share to be
                    modified belongs.
        :param sharename: Specifies the name of the share to be modified.
        :param fpg: Specifies the file provisioning group that <vfs> belongs.
            If this is not specified, the command will find out the file
            provisioning group based on the specified <vfs>. However, if <vfs>
            exists under multiple file provisioning groups, -fpg must be
            specified.
        :param fstore: Specifies the file store that the share to be modified
            belongs. If this is not specified, the <sharename> will be used as
            the file store name to identify the share.
        :param comment: Specifies any comments or additional information for
            the share. The comment can be up to 255 characters long.
            Unprintable characters are not allowed.

        :param abe: Access Based Enumeration. Specifies if users can see only
            the files and directories to which they have been allowed access
            on the shares.
        :param allowip: Specifies client IP addresses that are allowed access
            to the share. Use commas to separate the IP addresses.

            If <iplist> has a prefix (for example: +1.1.1.0,2.2.2.0):

            \+   add <iplist> to the existing allowed list. The IP addresses
            in <iplist> must not be in the existing allowed list.

            \-   remove <iplist> from the existing allowed list. The IP
            addresses in <iplist> must be already in the existing allowed list.

            If specified, the prefix will be applied to the entire <iplist>.
            If <iplist> has no prefix, <iplist> will be used as the new
            allowed list.
        :param denyip: Specifies client IP addresses that are denied access to
            the share. Use commas to separate the IP addresses.

            If <iplist> has a prefix (for example: +1.1.1.0,2.2.2.0):

            \+   add <iplist> to the existing denied list. The IP addresses
            in <iplist> must not be in the existing denied list.

            \-   remove <iplist> from the existing denied list. The IP
            addresses in <iplist> must already be in the existing denied list.

            If specified, the prefix will be applied to the entire <iplist>.
            If <iplist> has no prefix, <iplist> will be used as the new
            denied list.
        :param allowperm: Specifies the permissions that users/groups are
            allowed to access the share. <permlist> must be specified in the
            format of: "<user1>:<perm1>,<user2>:<perm2>,...". The <user> can be
            a user or group name specified using the same format as described
            in createfshare. <perm> must be "fullcontrol", "read", or "change".

            If <permlist> has a prefix (for example: +Everyone:read):

            \+   add <permlist> to the existing allowed list. Users/groups
            in <permlist> must not be in the existing allowed list.

            \-   remove <permlist> from the existing allowed list. Users/groups
            in <permlist> must be already in the existing allowed list.

            =   modify the existing allowed list with <permlist>. Users/groups
            in <permlist> must be already in the existing allowed list.

            If specified, the prefix will be applied to the entire <permlist>.
            If <permlist> has no prefix, <permlist> will be used as the
            new allowed list.
        :param denyperm: Specifies the permissions that users/groups are denied
            to access the share. <permlist> must be specified in the format of:
            "<user1>:<perm1>,<user2>:<perm2>,...". The <user> can be a user
            or group name specified using the same format as described in
            createfshare. <perm> must be "fullcontrol", "read", or "change".

            If <permlist> has a prefix (for example, +Everyone:read):

            \+   add <permlist> to the existing denied list. Users/groups
            in <permlist> must not be in the existing denied list.

            \-   remove <permlist> from the existing denied list. Users/groups
            in <permlist> must be already in the existing denied list.

            =   modify the existing denied list with <permlist>. Users/groups
            set in <permlist> must be already in the existing denied list.

            If specified, the prefix will be applied to the entire <permlist>.
            If <permlist> has no prefix, <permlist> will be used as the
            new denied list.
        :param cache: Specifies client-side caching for offline files. Valid
            values are:
            "off": The client must not cache any files from this share. The
            share is configured to disallow caching.
            "manual": The client must allow only manual caching for the files
            open from this share.
            "optimized": The client may cache every file that it opens from
            this share. Also, the client may satisfy the file requests from its
            local cache. The share is configured to allow automatic caching
            of programs and documents.
            "auto": The client may cache every file that it opens from this
            share. The share is configured to allow automatic caching of
            documents.
        :param ca: Continuous Availability. Specifies if SMB3 continuous
             availability features should be enabled for this share. If not
             specified, the default is 'true'. Valid values are 'true',
             'false' or None. The parameter is a Python string -- not a
             boolean.
        :param options: Specifies the new options to use for the share.
            This completely overwrites the options you set previously. Standard
            NFS export options except "no_subtree_check" are supported. Do not
            enter option "fsid", which is provided. If not specified, the
            following options will be automatically set:
            sync, auth_nlm, wdelay, sec=sys, no_all_squash, crossmnt, secure,
            subtree_check, hide, root_squash, ro.

            See linux exports(5) man page for detailed information on valid
            options.
        :param clientip: Specifies the clients that can access the share. The
            NFS client can be specified by the name (for example, sys1.hp.com),
            the name with a wildcard (for example, *.hp.com), or by its IP
            address. Use comma to separate the IP addresses.

            If <iplist> has a prefix (for example, +1.1.1.0,2.2.2.0):

            \+   add <iplist> to the existing list. IP addresses in <iplist>
            must not be in the existing list.

            \-   remove <iplist> from the existing list. IP addresses in
            <iplist> must be already in the existing list.

            If specified, the prefix will be applied to the entire <iplist>.
            If <iplist> has no prefix, <iplist> will be used as the new list.
        :param ssl: Specifies to enable or disable SSL.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_wrap_tcl
    @_run_with_cli
    @_protocol_first
    def getfshare(self, protocol, *sharename, **kwargs):
        r"""Show file shares information.

        The getfshare command displays file share information for supported
        protocols.

        PROTOCOLS

        smb
            Displays file shares information for SMB.
        nfs
            Displays file shares information for NFS.
        obj
            Displays file shares information for Object.

        :param protocol: The protocol {'nfs'|'smb'|'obj'}
        :param sharename: Displays only shares with names matching the
            specified <sharename> or one of glob-style patterns.
        :param \**kwargs: See below.
        :kwargs:
            * **fpg** -- Specifies the file provisioning group name. This
              limits the share output to those shares associated with the
              specified file provisioning group.
            * **vfs** -- Specifies the virtual file server name. This limits
              the share output to those shares associated with the specified
              virtual file server. If this option is specified, but -fpg is not
              specified, the command will find out the file provisioning group
              based on <vfs>. However, if <vfs> exists under multiple file
              provisioning groups, -fpg must be specified.
            * **fstore** -- Specifies the file store name. This limits the
              share output to only those shares associated with the specified
              file store. If this is specified, option -vfs must be specified.
            * **pat** -- Specifies the file share names using the  glob-style
              pattern. Shares which have the name matching any of the specified
              glob-style patterns will be displayed. The -pat option can
              specify a list of patterns, and it must be used if specifier
              <pattern> is used.
        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of fshares.
            }

        """

    @_run_with_cli
    @_protocol_first
    @_force_me
    def removefshare(self, protocol, vfs, sharename,
                     fpg=None, fstore=None):
        """Remove a file share from File Services cluster.

        PROTOCOLS

        smb
            Removes an SMB file share.
        nfs
            Removes an NFS file share.
        obj
            Removes an Object file share.

        :param protocol: The protocol {'nfs'|'smb'|'obj'}
        :param vfs: Specifies the virtual file server name.
        :param sharename: The name of the share to be removed.
        :param fpg: Specifies the file provisioning group that <vfs> belongs.
            If this is not specified, the command will find out the file
            provisioning group based on the specified <vfs>. However, if <vfs>
            exists under multiple file provisioning groups, -fpg must be
            specified.
        :param fstore: Specifies the file store that the file share to be
            removed belongs. If this is not specified, the <sharename> will be
            used as <fstore>.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    @_force_me
    def createfsnap(self, vfs, fstore, tag, retain=None, fpg=None):
        """Create a snapshot for File Services.

        If option -retain is specified and the file store already has the
        maximum number of snapshots taken, the oldest snapshot will be
        deleted first before the new snapshot is created. If the command fails
        to create the new snapshot, the deleted snapshot will not be restored.

        :param vfs: Specifies the name of the virtual file server.
        :param fstore: Specifies the name of the file store that the snapshot
                       will be taken. This is the path relative to <vfs>.
        :param tag: Specifies the suffix to be appended to the timestamp of
                    snapshot creation time in ISO 8601 date and time format,
                    which will become the name of the created file store
                    snapshot (for example: if "snapshot1" is being used as
                    <tag>, the snapshot  name will be
                    2013-12-17T215020_snapshot1). The name can be used as the
                    value of option -snapname to display or remove a snapshot.
        :param retain: Number of snapshots to retain with the specified tag.
                       Snapshots exceeding the count will be deleted, oldest
                       first. The valid range of <rcnt> is from 1 to 1024.
        :param fpg: Specifies the file provisioning group that <vfs> belongs.
                    If this is not specified, the command will find out the
                    file provisioning group based on the specified <vfs>.
                    However, if <vfs> exists under multiple file provisioning
                    groups, -fpg must be specified.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_wrap_tcl
    @_run_with_cli
    def getfsnap(self, *snapname, **kwargs):
        r"""Show snapshot information for File Services.

        :param snapname: Displays only snapshots with names matching the
                         specified <snapname> or one of glob-style patterns.
        :param \**kwargs: See below.
        :kwargs:
            * **fpg** -- Specifies the file provisioning group name. This
              option limits the snapshot output to those associated snapshots
              with the specified file provisioning group.
            * **vfs** -- Specifies the virtual file server name. This
              option limits the snapshot output to those snapshots associated
              with the specified virtual file server.
            * **fstore** -- Specifies the file store name. This option
              limits the snapshot output to only those snapshots associated
              with the specified file store.
            * **pat** -- Specifies the snapshot names using glob-style
              patterns. Snapshots which have the name matching any of the
              specified glob-style patterns will be displayed. Patterns
              can be repeated using a comma-separated list. The -pat
              option must be used if <pattern> specifier is used.
        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of fsnaps.
            }

        """

    @_run_with_cli
    @_force_me
    def removefsnap(self, vfs, fstore, snapname=None, fpg=None):
        """Remove file store snapshots from File Services.

        :param vfs: Specifies the virtual file server name.
        :param fstore: Specifies the file store name.
        :param snapname: Specifies the name of the snapshot to be removed. If
                         this is not specified, all snapshots of the file
                         store specified by <fstore> will be removed.
        :param fpg: Specifies the file provisioning group that <vfs> belongs.
                    If this is not specified, the command will find out the
                    file provisioning group based on the specified <vfs>.
                    However, if <vfs> exists under multiple file provisioning
                    groups, -fpg must be specified.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    def startfsnapclean(self, fpgname, resume=False, reclaimStrategy=None):
        """Start or resume an on-demand reclamation task.

        :param fpgname: Specifies the name of the file provisioning group.
        :param resume: Specifies a paused reclamation task needs to be resumed.
        :param reclaimStrategy: Specifies the strategy to be used while
                                reclaiming snap space.
            'maxspeed': Suggests optimize for speedy reclamation.
            'maxspace': Suggests optimize to reclaim maximum space.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_wrap_tcl
    @_run_with_cli
    def getfsnapclean(self, fpgname):
        """List details of snapshot reclamation tasks.

        The showfsnapclean command displays the details of an on-demand
        snapshot reclamation task active on a file provisioning group.

        :param fpgname: Specifies the name of the file provisioning group.
        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of fsnapcleans.
            }

        """

    @_run_with_cli
    def stopfsnapclean(self, fpgname, pause=False):
        """Stop or pause an on-demand reclamation task.

        The stopfsnapclean command stops or pauses an on-demand reclamation
        task on a file provisioning group.

        There can be only one reclamation task running on a file provisioning
        group. If we pause reclamation task, it will still be counted.

        If the task is not running, the following output is displayed:
        No reclamation task running on Storage Pool samplepool (Server error:
        400)

        :param fpgname: Specifies the name of the file provisioning group.
        :param pause: Specifies to pause a reclamation task.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_run_with_cli
    def setfsquota(self, vfsname, fpg=None, username=None, groupname=None,
                   fstore=None, scapacity=None, hcapacity=None, sfile=None,
                   hfile=None, clear=False, archive=False, restore=None):
        """Set the quotas for a specific virtual file server.

        :param vfsname: Specifies the name of the virtual file server
                        associated with the quotas.
        :param fpg: Specifies the name of the file provisioning group hosting
                    the virtual file server.
        :param username: The username of the quotas to be modified.

            If the user is configured on Active Directory,  use "setfs ad"
            to join Active Directory domain with <domain> if it  has not been
            done, and use "<domain>\\<uname>" or  "<ad-netbios>\\<uname>"
            to specify the user (for example, -username  example.com\aduser).
            The "<ad-netbios>" is Active Directory NetBIOS name,  which can
            be found by running "showfs -ad".

            If the user is configured on the LDAP server,  use "setfs ldap"
            to create LDAP configuration with <ldap-netbios> if it has not been
            done, and use "<ldap-netbios>\\<username>" to specify the user
            (for example, -username ldaphost\\ldapuser). The "<ldap-netbios>"
            is the LDAP server NetBIOS name, which can be found by running
            "showfs -ldap".
        :param groupname: The groupname of the quotas to be modified.

            If the group is configured on Active Directory, use "setfs ad"
            to join Active Directory domain with <domain> if it has not been
            done, and use "<domain>\\<gname>" or "<ad-netbios>\\<uname>"
            to specify the user (for example, -groupname example.com\adgroup).
            The <ad-netbios> is Active Directory NetBIOS name, which can be
            found by running "showfs -ad".

            If the group is configured on the LDAP server, use "setfs ldap"
            to create LDAP configuration with <ldap-netbios> if it has not been
            done, and use "<ldap-netbios>\\<gname>" to specify the user (for
            example, -groupname ldaphost\\ldapgroup).
        :param fstore: The path to the fstore to which you wish to apply
             quotas.
        :param scapacity: An integer value in MB for the soft capacity storage
             quota.
        :param hcapacity: An integer value in MB for the hard capacity storage
             quota.
        :param sfile: An integer limit of the number of files for the soft file
             quota.
        :param hfile: An integer limit of the number of files for the hard file
             quota.
        :param clear: Clears the quotas of the specified object.
        :param archive: Stores the quota information associated with the VFS in
             a file.
        :param restore: Applies the quota information stored in the file to the
             VFS.
        :return: List of strings.  Lines of output from the CLI command.
        """

    @_wrap_tcl
    @_run_with_cli
    def getfsquota(self, username=None, groupname=None, fstore=None,
                   vfs=None, fpg=None):
        """Show the quotas for File Services.

        :param username: The user name of the quotas to be displayed.
        :param groupname: The group name of the quotas to be displayed.
        :param fstore: The file store of the quotas to be displayed.
        :param vfs: Specifies the name of the virtual file server associated
                    with the quotas.
        :param fpg: Specifies the name of the file provisioning group hosting
                    the virtual file server.
        :return: dict with message, total and members

        .. code-block:: python

            result = {
                'message': None,  # Error message, if any.
                'total': 0        # Number of members returned.
                'members': [],    # List containing dict of fsquotas.
            }

        """
