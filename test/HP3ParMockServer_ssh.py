# (c) Copyright 2015-2016 Hewlett Packard Development Company, L.P.
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
""" Test SSH server."""

import argparse
import logging
import os
import shlex
import socket
import sys
import threading

import paramiko


paramiko.util.log_to_file('paramiko_server.log')


class CliParseException(Exception):
    pass


class CliArgumentParser(argparse.ArgumentParser):

    def error(self, message):
        usage = super(CliArgumentParser, self).format_help()
        full_message = "%s\r\n%s" % (message, usage)
        raise CliParseException(full_message)

    def parse_args(self, *args):
        return super(CliArgumentParser, self).parse_args(args[1:])


class Cli(object):

    def __init__(self):
        self.log_name = 'paramiko.3PARCLI'
        self.logger = paramiko.util.get_logger(self.log_name)

        self.fpgs = {}
        self.vfss = {}

    def do_cli_other(self, *args):
        msg = 'FAIL! Mock SSH CLI does not know how to "%s".' % ' '.join(args)
        self.logger.log(logging.ERROR, msg)
        return msg

    def do_cli_exit(self, *args):
        self.logger.log(logging.INFO, "quiting... g'bye")
        return ''

    def do_cli_quit(self, *args):
        self.logger.log(logging.INFO, "quiting... g'bye")
        return ''

    def do_cli_setclienv(self, *args):
        command_string = ' '.join(args)
        self.logger.log(logging.INFO, command_string)
        return None

    def do_cli_removefpg(self, *args):

        parser = CliArgumentParser(prog=args[0])
        parser.add_argument(
            '-f', default=False, action="store_true",
            help="Specifies that the command is forced. If this option is "
                 "not used, the command requires confirmation before "
                 "proceeding with its operation.")
        parser.add_argument(
            '-forget',
            help="Removes the specified file provisioning group which is "
                 "involved in Remote DR, keeping the virtual volume intact.")
        parser.add_argument(
            '-wait', default=False, action="store_true",
            help="Wait until the associated task is completed before "
                 "proceeding. This option will produce verbose task "
                 "information.")
        parser.add_argument(
            "fpgname",
            help="fpgname is the name of the file provisioning group to be "
                 "removed. This specifier can be repeated to remove multiple "
                 "common provisioning groups."
                 ""
                 "OR"
                 ""
                 "Specifies a glob-style pattern. This specifier can be "
                 "repeated to remove multiple common provisioning groups. "
                 "If this specifier is not used, the <fpgname> specifier must "
                 "be used. See help on sub,globpat for more information.")

        opts = parser.parse_args(*args)

        fpg = self.fpgs.pop(opts.fpgname)

        if fpg is None:
            return "File Provisioning Group: %s did not exist." % fpg
        else:
            return "File Provisioning Group: %s removed." % fpg

    def do_cli_createfpg(self, *args):

        parser = CliArgumentParser(prog=args[0])
        parser.add_argument(
            '-comment',
            help="Specifies the textual description of the "
                 "file provisioning group.")
        parser.add_argument(
            '-full', default=False, action="store_true",
            help="Specifies the textual description of the "
                 "file provisioning group.")
        parser.add_argument(
            '-node',
            help="Bind the created file provisioning group to the specified "
                 "node.")
        parser.add_argument(
            '-recover',
            help="Recovers the specified file provisioning group which is "
                 "involved in Remote DR and that was removed using the "
                 "-forget option.")
        parser.add_argument(
            '-wait', default=False, action="store_true",
            help="Wait until the associated task is completed before "
                 "proceeding. This option will produce verbose task "
                 "information.")
        parser.add_argument(
            "cpgname",
            help="The CPG where the VVs associated with the file provisioning "
                 "group will be created")
        parser.add_argument(
            "fpgname",
            help="The name of the file provisioning group to be created")
        parser.add_argument(
            "size",
            help="""
The size of the file provisioning group to be created.
The specified size must be between 1T and 32T.
A suffix (with no whitespace before the suffix) will
modify the units to TB (t or T suffix).
            """)

        self.logger.log(
            logging.WARNING,
            "createfpg with argparser args %s" % ','.join(args))

        opts = parser.parse_args(*args)

        # Don't know what CPGs are in flask, yet, so just
        # use hard-coded value for test case.
        cpg = opts.cpgname
        if cpg and cpg == 'thiscpgdoesnotexist':
            return 'Error: Invalid CPG name: %s\r' % cpg
        # ... and use hard-coded value for domain test case.
        if cpg and cpg.startswith('UT3_'):
            return '%s belongs to domain HARDCODED which cannot be used for ' \
                   'File Services.\r' % cpg

        # Validate size.
        size = opts.size
        units = size[-1]
        if units.upper() != 'T':
            return 'The suffix, %s, for size is invalid.\r' % units

        if opts.fpgname in self.fpgs:
            return "Error: FPG %s already exists\r" % opts.fpgname

        self.fpgs[opts.fpgname] = opts

        return ('File Provisioning Group %s created.\n'
                'File Provisioning Group %s activated.' % (opts.fpgname,
                                                           opts.fpgname))

    def do_cli_createvfs(self, *args):

        parser = CliArgumentParser(prog=args[0])
        parser.add_argument(
            '-comment',
            help="Specifies any additional textual information.")
        parser.add_argument(
            '-bgrace', default='3600',
            help="The block grace time in seconds for quotas within the VFS.")
        parser.add_argument(
            '-igrace', default='3600',
            help="The inode grace time in seconds for quotas within the VFS.")
        parser.add_argument(
            '-fpg',
            help="The name of an existing File Provisioning Group in which "
                 "the VFS should be created.")
        parser.add_argument(
            '-cpg',
            help="The CPG in which the File Provisioning Group should be "
                 "created.")
        parser.add_argument(
            '-size',
            help="The size of the File Provisioning Group to be created.")
        parser.add_argument(
            '-node',
            help="The node to which the File Provisioning Group should be "
                 "assigned. Can only be used when creating the FPG with the "
                 "-cpg option.")
        parser.add_argument(
            '-vlan',
            help="The VLAN ID associated with the VFSIP.")
        parser.add_argument(
            '-wait', default=False, action="store_true",
            help="Wait until the associated task is completed before "
                 "proceeding. This option will produce verbose task "
                 "information.")
        parser.add_argument(
            "ipaddr",
            help="The IP address to which the VFS should be assigned")
        parser.add_argument(
            "subnet",
            help="The subnet for the IP Address.")
        parser.add_argument(
            "vfsname",
            help="The name of the VFS to be created.")

        self.logger.log(
            logging.INFO,
            "createvfs with argparser args %s" % ','.join(args))

        opts = parser.parse_args(*args)

        bgrace = -1
        try:
            bgrace = int(opts.bgrace)
        except Exception:
            pass

        if bgrace < 1 or bgrace > 2147483647:
            return 'bgrace value should be between 1 and 2147483647\r'

        igrace = -1
        try:
            igrace = int(opts.igrace)
        except Exception:
            pass

        if igrace < 1 or igrace > 2147483647:
            return 'igrace value should be between 1 and 2147483647\r'

        if opts.vfsname in self.vfss:
            return 'VFS "%s" already exists within FPG %s\r' % (opts.vfsname,
                                                                opts.fpg)

        self.vfss[opts.vfsname] = opts

        return 'Created VFS "%s" on FPG %s.' % (opts.vfsname, opts.fpg)

    def do_cli_showfpg(self, *args):

        usage = """
SYNTAX
    showfpg [options] [<fpgname>]

OPTIONS
    -d
        Detailed output.
"""

        details = False
        fpg_name = None
        for arg in args[1:]:
            if arg == '-d':
                if details:
                    return "Option -d already specified"
                else:
                    details = True
            elif arg[0] == '-':
                return "showfpg: Invalid option %s\r\n\r\n%s" % (arg, usage)
            elif not fpg_name:
                fpg_name = arg

        if fpg_name:
            if fpg_name in self.fpgs:
                return [
                    "Header",
                    "------",
                    self.fpgs[fpg_name]  # TODO: formatting
                ]
            else:
                return "File Provisioning Group: %s not found" % fpg_name
        else:
            if self.fpgs:
                ret = [
                    "Header",
                    "------",
                    "foo"
                ]
                # for fpg in self.fpgs:
                #     ret = '\n'.join((ret, fpg))

                return ret

            else:
                return "No File Provisioning Groups found."

    def do_cli_gettpdinterface(self, *args):
        tpdinterface = open('./test/tpdinterface/tpdinterface.tcl', 'r')
        tcl = tpdinterface.read()
        self.logger.log(
            logging.ERROR,
            tcl)
        tpdinterface.close()
        return tcl

    def do_cli_getfs(self, *args):
        ret = \
            '{' \
            '{0 - Yes running Yes Yes 1.0.0.5-20140730 0:2:1,0:2:2 1 1500} '\
            '{1 - Yes running No Yes 1.0.0.5-20140730 1:2:1,1:2:2 1 1500} ' \
            '{2 - No Unknown No No - - - -} ' \
            '{3 - No Unknown No No - - - -}' \
            '} ' \
            '{' \
            '{0 unityUserAddr5a5c7103-252a-413a-ae81-49688ea7ece0 ' \
            '10.50.158.1 255.255.0.0 0} ' \
            '{1 unityUserAddrcd512782-1e2e-4a1d-be71-3b568b65594d ' \
            '10.50.158.2 255.255.0.0 0}' \
            '} ' \
            '{unityUserGWAddr291e4af6-925f-4f9d-b4eb-305a4b21fad5 10.50.0.1} '\
            '{10.50.0.5 csim.rose.hp.com} ' \
            '{{defaultProfile 80 443 true 5 58 8192 8192}} ' \
            '{} {} {{ActiveDirectory Local}} ' \
            '{false ' \
            '{' \
            '0.centos.pool.ntp.org ' \
            '1.centos.pool.ntp.org ' \
            '2.centos.pool.ntp.org}}'
        return ret

    def do_cli_getfpg(self, *args):

        filtered_fpgs = []
        if len(args) > 1:
            for fpg in args[1:]:
                if not fpg in self.fpgs:
                    return 'File Provisioning Group: %s not found\r' % fpg
                else:
                    filtered_fpgs.append(self.fpgs[fpg])
        else:
            filtered_fpgs = list(self.fpgs.values())

        # Place-holders for most values set outside of loop.
        # Param based on the create params (or generated) inside the loop.

        fpg_dict = {
            'uuid': '49ec3e7e-d7af-4e73-9536-79065483164f',
            'generation': '1',
            'hosts': '{node1fs node0fs}',
            'createTime': '1424473547353',
            'number': '5',
            'availCapacityKiB': '1073031792',
            'freeCapacityKiB': '1073031792',
            'capacityKiB': '1073741824',
            'fFree': '2216786133',
            'filesUsed': '36',

            'domains_name': 'd457e1ab-9d92-4355-a639-51cefbb93068',
            'domains_owner': '1',
            'domains_filesets': 'fileset1',
            'domains_volumes': '200',
            'domains_hosts': '{1 0}',
            'domains_ipfsType': 'ADE',

            'segments_number': '1',
            'segments_unavailable': 'false',
            'segments_readOnly': 'false',
            'segments_ipfsType': 'ADE',
            'segments_domain': 'd457e1ab-9d92-4355-a639-51cefbb93068',
            'segments_fileset': 'fileset1',
            'segments_availCapacityKiB': '1073031792',
            'segments_freeCapacityKiB': '1073031792',
            'segments_capacityKiB': '1073741824',
            'segments_fFree': '2216786133',
            'segments_files': '2216786169',

            'volumes_name': '{}',
            'volumes_lunUuid': '200',
            'volumes_hosts': '{1 0}',
            'volumes_capacityInMb': '1048576',

            'mountStates': 'ACTIVATED',
            'primaryNode': '1',
            'alternateNode': '0',
            'currentNode': '1',
            'comment': '{}',
            'overallStateInt': '1',
            'compId': '10465140418516302068',
            'usedCapacityKiB': '710032',
            'freezeState': 'NOT_FROZEN',
            'isolationState': 'ACCESSIBLE',
        }

        fpg_list = []
        for fpg in filtered_fpgs:
            fpgname = fpg.fpgname
            fpg_dict['fpgname'] = fpgname
            fpg_dict['mountpath'] = ''.join(('/', fpgname))
            fpg_dict['vvs'] = '.'.join((fpgname, '1'))
            fpg_dict['defaultCpg'] = fpg.cpgname
            fpg_dict['domains_fsname'] = fpgname
            fpg_dict['segments_fsname'] = fpgname

            fpg_tcl_format = (
                '{'
                '%(fpgname)s '
                '%(uuid)s '
                '%(generation)s '
                '%(mountpath)s '
                '%(hosts)s '
                '%(createTime)s '
                '%(number)s '
                '%(availCapacityKiB)s '
                '%(freeCapacityKiB)s '
                '%(capacityKiB)s '
                '%(fFree)s '
                '%(filesUsed)s '
                '%(vvs)s '
                '%(defaultCpg)s '
                '{{'
                '%(domains_name)s '
                '%(domains_owner)s '
                '%(domains_fsname)s '
                '%(domains_filesets)s '
                '%(domains_volumes)s '
                '%(domains_hosts)s '
                '%(domains_ipfsType)s '
                '}}'
                '{{'
                '%(segments_fsname)s '
                '%(segments_number)s '
                '%(segments_unavailable)s '
                '%(segments_readOnly)s '
                '%(segments_ipfsType)s '
                '%(segments_domain)s '
                '%(segments_fileset)s '
                '%(segments_availCapacityKiB)s '
                '%(segments_freeCapacityKiB)s '
                '%(segments_capacityKiB)s '
                '%(segments_fFree)s '
                '%(segments_files)s '
                '}}'
                '{{'
                '%(volumes_name)s '
                '%(volumes_lunUuid)s '
                '%(volumes_hosts)s '
                '%(volumes_capacityInMb)s '
                '}}'
                '%(mountStates)s '
                '%(primaryNode)s '
                '%(alternateNode)s '
                '%(currentNode)s '
                '%(comment)s '
                '%(overallStateInt)s '
                '%(compId)s '
                '%(usedCapacityKiB)s '
                '%(freezeState)s '
                '%(isolationState)s '
                '}'
            )
            fpg_list.append(fpg_tcl_format % fpg_dict)

        return ' '.join(fpg_list) if fpg_list else (
            'No File Provisioning Groups found.')

    def do_cli_getvfs(self, *args):

        parser = CliArgumentParser(prog=args[0])
        parser.add_argument(
            '-d', default=False, action="store_true",
            help="Detailed output.")
        parser.add_argument(
            '-fpg',
            help="Limit the display to VFSs contained within the "
                 "File Provisioning Group.")
        parser.add_argument(
            '-vfs',
            help="Limit the display to the specified VFS name.")

        self.logger.log(
            logging.INFO,
            "getvfs with argparser args %s" % ','.join(args))

        opts = parser.parse_args(*args)

        filtered_vfss = []
        if opts.fpg or opts.vfs:
            for vfs in list(self.vfss.values()):
                if opts.vfs and vfs.vfsname != opts.vfs:
                    continue
                if opts.fpg and vfs.fpg != opts.fpg:
                    continue

                filtered_vfss.append(vfs)
        else:
            filtered_vfss = list(self.vfss.values())

        # Place-holders for most values set outside of loop.
        # Param based on the create params (or generated) inside the loop.

        vfs_dict = {
            'uuid': '49ec3e7e-d7af-4e73-9536-79065483164f',
            'comment': '{}',
            'overallStateInt': '1',
            'compId': '10465140418516302068',
        }

        vfs_list = []
        for vfs in filtered_vfss:
            vfsname = vfs.vfsname
            vfs_dict['vfsname'] = vfsname
            vfs_dict['fspname'] = vfs.fpg
            vfs_dict['vfsip'] = 'todo'
            vfs_dict['certs'] = 'todo'
            vfs_dict['bgrace'] = vfs.bgrace
            vfs_dict['igrace'] = vfs.igrace
            vfs_dict['uuid'] = 'todo'

            vfs_tcl_format = (
                '{'
                '%(vfsname)s '
                '%(fspname)s '
                '%(vfsip)s '
                '%(overallStateInt)s '
                '%(comment)s '
                '%(certs)s '
                '%(bgrace)s '
                '%(igrace)s '
                '%(uuid)s '
                '%(compId)s '
                '}'
            )
            vfs_list.append(vfs_tcl_format % vfs_dict)

        return ' '.join(vfs_list) if vfs_list else ''

    def do_cli_removevfs(self, *args):

        parser = CliArgumentParser(prog=args[0])
        parser.add_argument(
            '-f', default=False, action="store_true",
            help="Specifies that the command is forced.")
        parser.add_argument(
            '-fpg',
            help="Name of the File Provisioning Group containing the VFS.")
        parser.add_argument(
            "vfs",
            help="The name of the VFS to be removed.")

        self.logger.log(
            logging.INFO,
            "removevfs with argparser args %s" % ','.join(args))

        opts = parser.parse_args(*args)

        if opts.fpg and not opts.fpg in self.fpgs:
            return 'File Provisioning Group: %s not found\r' % opts.fpg

        for vfs in list(self.vfss.values()):
            if vfs.vfsname == opts.vfs and (
               opts.fpg is None or vfs.fpg == opts.fpg):
                self.vfss.pop(vfs.vfsname)
                return "deleted VFS"
        else:
            return ('Virtual file server %s was not found in any existing '
                    'file provisioning group.\r' % opts.vfs)

    def do_cli_getfsip(self, *args):

        parser = CliArgumentParser(prog=args[0])
        parser.add_argument(
            '-fpg',
            help="Specifies the File Provisioning Group in which the "
                 "Virtual File Server was created.")
        parser.add_argument(
            'vfs',
            help="Specifies the Virtual File Server which is to have its "
                 "network config modified.")

        self.logger.log(
            logging.INFO,
            "getfsip with argparser args %s" % ','.join(args))

        opts = parser.parse_args(*args)

        if opts.fpg and not opts.fpg in self.fpgs:
            return 'File Provisioning Group: %s not found\r' % opts.fpg

        fsips = []
        for vfs in list(self.vfss.values()):
            if opts.vfs and vfs.vfsname != opts.vfs:
                continue
            if opts.fpg and vfs.fpg != opts.fpg:
                continue
            fsips.append({
                'id': '012345679abcdef',
                'vfs': vfs.vfsname,
                'fpg': vfs.fpg,
                'ipaddr': vfs.ipaddr,
                'subnet': vfs.subnet,
                'vlan': vfs.vlan or '0',
                'type': 'user',
            })

        if not fsips:
            return 'Invalid VFS %s\r' % opts.vfs

        fsip_list = []
        for fsip in fsips:
            tcl_format = (
                '{'
                '%(id)s '
                '%(fpg)s '
                '%(vfs)s '
                '%(vlan)s '
                '%(subnet)s '
                '%(ipaddr)s '
                '%(type)s'
                '}'
            )
            fsip_list.append(tcl_format % fsip)

        if fsip_list:
            return '{%s}' % ' '.join(fsip_list)
        else:
            return 'No FSIPS found.'

    def do_cli_showpatch(self, *args):

        self.logger.log(logging.ERROR, "TEST SHOWPATCH")
        print(args)

        if len(args) > 1:
            self.logger.log(logging.ERROR, "TEST SHOWPATCH len %s" % len(args))
            self.logger.log(logging.ERROR, "TEST SHOWPATCH 1) %s" % args[1])
            if args[1] == '-hist':
                return "patch history not faked yet"

            elif args[1] == '-d':
                patch_id = args[2]
                return "Patch " + patch_id + " not recognized."

        return "showpatch needs more arg checking and implementing"

    def do_cli_showvv(self, *args):
        # NOTE(aorourke): Only the pattern matching (-p) for volumes whose
        # copyof column matches the volumes name (-copyof) is supported in
        # the mocked version of showvv.
        parser = CliArgumentParser(prog=args[0])
        parser.add_argument(
            '-p', default=False, action="store_true",
            help="Pattern for matching VVs to show.")
        parser.add_argument(
            '-copyof', default=True, action="store_true",
            help="Show only VVs whose CopyOf column matches one more of the "
                 "vvname_or_patterns.")
        parser.add_argument(
            "name",
            help="The name of the VV to show.")

        self.logger.log(
            logging.INFO,
            "showvv with argparser args %s" % ','.join(args))

        opts = parser.parse_args(*args)

        if not opts.p or not opts.copyof or not opts.name:
            return "no vv listed"

        if "VOLUME1_UNIT_TEST" in opts.name:
            cli_out = """
,,,,,,,,--Rsvd(MB)---,,,-(MB)-\r\n
Id,Name,Prov,Type,CopyOf,BsId,Rd,-Detailed_State-,Adm,Snp,Usr,VSize\r\n
123,SNAP_UNIT_TEST1,snp,vcopy,myVol,123,RO,-,-,-,-,-\r\n
124,SNAP_UNIT_TEST2,vcopy,myVol,124,RO,-,-,-,-,-\r\n
--------------------------------\r\n
2,total\r\n
"""
        else:
            cli_out = "no vv listed"

        return cli_out

    def process_command(self, cmd):
        self.logger.log(logging.INFO, cmd)
        if cmd is None:
            print("returnNone")
            return ''
        args = shlex.split(cmd)
        if args:
            method = getattr(self, 'do_cli_' + args[0], self.do_cli_other)
            try:
                return method(*args)
            except Exception as cmd_exception:
                return str(cmd_exception)
        else:
            return ''


class ParamikoServer(paramiko.ServerInterface):

    def __init__(self):
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_password(self, username, password):
        # if (username == '3paradm') and (password == '3pardata'):
            # return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'password,publickey,none'

    def check_channel_shell_request(self, c):
        self.event.set()
        return True

    def check_channel_pty_request(self, c, term, width, height, pixelwidth,
                                  pixelheight, modes):
        return True


if __name__ == "__main__":

    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 2200

    key_file = os.path.expanduser('~/.ssh/id_rsa')
    host_key = paramiko.RSAKey(filename=key_file)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', int(port)))
    s.listen(60)
    print("Listening for SSH client connections...")
    connection, address = s.accept()
    transport = None
    channel = None
    try:
        transport = paramiko.Transport(connection)
        transport.load_server_moduli()
        transport.add_server_key(host_key)
        server = ParamikoServer()
        transport.start_server(server=server)

        cliProcessor = Cli()

        while True:
            channel = transport.accept(60)
            if channel is None:
                print("Failed to get SSH channel.")
                sys.exit(1)

            print("Connected")
            server.event.wait(10)

            if not server.event.isSet():
                print("No shell set")
                sys.exit(1)

            fio = channel.makefile('rU')
            commands = []
            command = None
            while not (command == 'exit' or command == 'quit'):
                command = fio.readline().strip('\r\n')
                commands.append(command)

            to_send = '\r\n'.join(commands)
            channel.send(to_send)

            output = ['']
            prompt = "FAKE-3PAR-CLI cli% "
            for cmd in commands:
                output.append('%s%s' % (prompt, cmd))
                result = cliProcessor.process_command(cmd)
                if result is not None:
                    output.append(result)
            output_to_send = '\r\n'.join(output)
            channel.send(output_to_send)
            channel.close()
            print("Disconnected")

    finally:
        if channel:
            channel.close()
        if transport:
            try:
                transport.close()
                print("transport closed")
            except Exception as e:
                print("transport close exception %s" % e)
                pass
