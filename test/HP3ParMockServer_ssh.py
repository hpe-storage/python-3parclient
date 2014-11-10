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
""" Test SSH server."""

import argparse
import logging
import os
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

    def do_cli_other(self, *args):
        msg = "FAIL!  What is: %s ???" % ' '.join(args)
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
modify the units to GB (g or G suffix) or TB (t or T suffix).
            """)

        self.logger.log(
            logging.WARNING,
            "createfpg with argparser args %s" % ','.join(args))

        opts = parser.parse_args(*args)

        fpg = opts.fpgname

        if fpg in self.fpgs:
            return "File Provisioning Group: %s already exists" % fpg

        self.fpgs[fpg] = opts

        return 'success?'

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
        tpdinterface = open('./tpdinterface/tpdinterface.tcl', 'r')
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
            '{} {} {{{ActiveDirectory Local}}} ' \
            '{false ' \
            '{' \
            '0.centos.pool.ntp.org ' \
            '1.centos.pool.ntp.org ' \
            '2.centos.pool.ntp.org}}'
        return ret

    def do_cli_showpatch(self, *args):

        self.logger.log(logging.ERROR, "TEST SHOWPATCH")
        print args

        if len(args) > 1:
            self.logger.log(logging.ERROR, "TEST SHOWPATCH len %s" % len(args))
            self.logger.log(logging.ERROR, "TEST SHOWPATCH 1) %s" % args[1])
            if args[1] == '-hist':
                return "patch history not faked yet"

            elif args[1] == '-d':
                patch_id = args[2]
                return "Patch " + patch_id + " not recognized."

        return "showpatch needs more arg checking and implementing"

    def process_command(self, cmd):
        self.logger.log(logging.INFO, cmd)
        if cmd is None:
            print "returnNone"
            return ''
        args = cmd.split()
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
    print "Listening for SSH client connections..."
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
                print "Failed to get SSH channel."
                sys.exit(1)

            print "Connected"
            server.event.wait(10)

            if not server.event.isSet():
                print "No shell set"
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
            print "Disconnected"

    finally:
        if channel:
            channel.close()
        if transport:
            try:
                transport.close()
                print "transport closed"
            except Exception as e:
                print ("transport close exception %s" % e)
                pass
