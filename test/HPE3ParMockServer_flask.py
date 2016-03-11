import flask
import re
import pprint
import json
import random
import string
import argparse
import uuid
from time import gmtime, strftime
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException

# 3PAR error code constants
INV_USER_PASS = 5
INV_INPUT = 12
EXISTENT_CPG = 14
NON_EXISTENT_CPG = 15
EXISTENT_HOST = 16
NON_EXISTENT_HOST = 17
NON_EXISTENT_VLUN = 19
EXISTENT_VOL = 22
NON_EXISTENT_VOL = 23
EXPORTED_VLUN = 26
TOO_LARGE = 28
NON_EXISTENT_DOMAIN = 38
INV_INPUT_WRONG_TYPE = 39
INV_INPUT_MISSING_REQUIRED = 40
INV_INPUT_EXCEEDS_RANGE = 43
INV_INPUT_PARAM_CONFLICT = 44
INV_INPUT_EMPTY_STR = 45
INV_INPUT_BAD_ENUM_VALUE = 46
INV_INPUT_PORT_SPECIFICATION = 55
INV_INPUT_EXCEEDS_LENGTH = 57
EXISTENT_ID = 59
INV_INPUT_ILLEGAL_CHAR = 69
EXISTENT_PATH = 73
NON_EXISTENT_SET = 77
HOST_IN_SET = 77
INV_INPUT_ONE_REQUIRED = 78
NON_EXISTENT_PATH = 80
NON_EXISTENT_QOS_RULE = 100
EXISTENT_SET = 101
EXISTENT_QOS_RULE = 114
INV_INPUT_BELOW_RANGE = 115
INV_INPUT_QOS_TARGET_OBJECT = 117
NON_EXISTENT_TASK = 145
INV_INPUT_VV_GROW_SIZE = 152
VV_NEW_SIZE_EXCEED_CPG_LIMIT = 153
NON_EXISTENT_OBJECT_KEY = 180
EXISTENT_OBJECT_KEY = 181
NON_EXISTENT_RCOPY_GROUP = 187
EXISTENT_RCOPY_GROUP = 237

# Remote Copy Actions
ADMIT_VV = 1
DISMISS_VV = 2
START_GROUP = 3
STOP_GROUP = 4
SYNC_GROUP = 5
FAILOVER_GROUP = 7

# Remote Copy States
RCOPY_STARTED = 3
RCOPY_STOPPED = 5

parser = argparse.ArgumentParser()
parser.add_argument("-debug", help="Turn on http debugging",
                    default=False, action="store_true")
parser.add_argument("-user", help="User name")
parser.add_argument("-password", help="User password")
parser.add_argument("-port", help="Port to listen on", type=int, default=5000)
args = parser.parse_args()
user_name = args.user
user_pass = args.password
debugRequests = False
if "debug" in args and args.debug:
    debugRequests = True

# __all__ = ['make_json_app']


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def make_json_app(import_name, **kwargs):
    """
    Create a JSON-oriented Flask app.

    All error responses that you don't specifically
    manage yourself will have application/json content
    type, and will contain JSON like this (just an example):

    { "message": "405: Method Not Allowed" }

    """
    def make_json_error(ex):
        pprint.pprint(ex)
        # pprint.pprint(ex.code)
        response = flask.jsonify(message=str(ex))
        # response = jsonify(ex)
        response.status_code = (ex.code
                                if isinstance(ex, HTTPException)
                                else 500)
        pprint.pprint(response)
        return response

    app = flask.Flask(import_name, **kwargs)
    # app.debug = True
    app.secret_key = id_generator(24)

    for code in list(default_exceptions.keys()):
        app.error_handler_spec[None][code] = make_json_error

    return app

app = make_json_app(__name__)
session_key = id_generator(24)


def debugRequest(request):
    if debugRequests:
        print("\n")
        pprint.pprint(request)
        pprint.pprint(request.headers)
        pprint.pprint(request.data)


def throw_error(http_code, error_code=None, desc=None, debug1=None,
                debug2=None):
    if error_code:
        info = {'code': error_code, 'desc': desc}
        if debug1:
            info['debug1'] = debug1
        if debug2:
            info['debug2'] = debug2
        flask.abort(flask.Response(json.dumps(info), status=http_code))
    else:
        flask.abort(http_code)


@app.route('/')
def index():
    debugRequest(flask.request)
    if 'username' in flask.session:
        return 'Logged in as %s' % flask.escape(flask.session['username'])
    flask.abort(401)


@app.route('/api/v1/throwerror')
def errtest():
    debugRequest(flask.request)
    throw_error(405, 123, 'testing throwing an error',
                'debug1 message', 'debug2 message')


@app.errorhandler(404)
def not_found(error):
    debugRequest(flask.request)
    return flask.Response("%s has not been implemented" % flask.request.path,
                          status=501)


@app.route('/api/v1/credentials', methods=['GET', 'POST'])
def credentials():
    debugRequest(flask.request)

    if flask.request.method == 'GET':
        return 'GET credentials called'

    elif flask.request.method == 'POST':
        data = json.loads(flask.request.data.decode('utf-8'))

        if data['user'] == user_name and data['password'] == user_pass:
            # do something good here
            try:
                resp = flask.make_response(json.dumps({'key': session_key}),
                                           201)
                resp.headers['Location'] = ('/api/v1/credentials/%s' %
                                            session_key)
                flask.session['username'] = data['user']
                flask.session['password'] = data['password']
                flask.session['session_key'] = session_key
                return resp
            except Exception as ex:
                pprint.pprint(ex)

        else:
            # authentication failed!
            throw_error(403, INV_USER_PASS, "invalid username or password")


@app.route('/api/v1/credentials/<session_key>', methods=['DELETE'])
def logout_credentials(session_key):
    debugRequest(flask.request)
    flask.session.clear()
    return 'DELETE credentials called'


# CPG

@app.route('/api/v1/cpgs', methods=['POST'])
def create_cpgs():
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'name': None, 'growthIncrementMB': None,
                  'growthLimitMB': None,
                  'usedLDWarningAlertMB': None, 'domain': None,
                  'LDLayout': None}

    valid_LDLayout_keys = {'RAIDType': None, 'setSize': None, 'HA': None,
                           'chuckletPosRef': None, 'diskPatterns': None}

    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)
        elif 'LDLayout' in list(data.keys()):
            layout = data['LDLayout']
            for subkey in list(layout.keys()):
                if subkey not in valid_LDLayout_keys:
                    throw_error(400, INV_INPUT,
                                "Invalid Parameter '%s'" % subkey)

    if 'domain' in data and data['domain'] == 'BAD_DOMAIN':
        throw_error(404, NON_EXISTENT_DOMAIN,
                    "Non-existing domain specified.")

    for cpg in cpgs['members']:
        if data['name'] == cpg['name']:
            throw_error(409, EXISTENT_CPG,
                        "CPG '%s' already exist." % data['name'])

    cpgs['members'].append(data)
    cpgs['total'] = cpgs['total'] + 1

    return flask.make_response("", 200)


@app.route('/api/v1/cpgs', methods=['GET'])
def get_cpgs():
    debugRequest(flask.request)

    # should get it from global cpgs
    resp = flask.make_response(json.dumps(cpgs), 200)
    return resp


@app.route('/api/v1/cpgs/<cpg_name>', methods=['GET'])
def get_cpg(cpg_name):
    debugRequest(flask.request)

    for cpg in cpgs['members']:
        if cpg['name'] == cpg_name:
            resp = flask.make_response(json.dumps(cpg), 200)
            return resp

    throw_error(404, NON_EXISTENT_CPG, "CPG '%s' doesn't exist" % cpg_name)


@app.route('/api/v1/spacereporter', methods=['POST'])
def get_cpg_available_space():
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    for cpg in cpgs['members']:
        if cpg['name'] == data['cpg']:
            fake_cpg_info = {
                "rawFreeMiB": 7630848,
                "usableFreeMiB": 3815424
            }
            resp = flask.make_response(json.dumps(fake_cpg_info), 200)
            return resp

    throw_error(404, NON_EXISTENT_CPG, "CPG '%s' doesn't exist" % data['cpg'])


@app.route('/api/v1/cpgs/<cpg_name>', methods=['DELETE'])
def delete_cpg(cpg_name):
    debugRequest(flask.request)

    for cpg in cpgs['members']:
        if cpg['name'] == cpg_name:
            cpgs['members'].remove(cpg)
            return flask.make_response("", 200)

    throw_error(404, NON_EXISTENT_CPG, "CPG '%s' doesn't exist" % cpg_name)


# Host Set

def get_host_set_for_host(name):
    for host_set in host_sets['members']:
        for host_name in host_set['setmembers']:
            if host_name == name:
                return host_set['name']
    return None


@app.route('/api/v1/hostsets', methods=['GET'])
def get_host_sets():
    debugRequest(flask.request)
    resp = flask.make_response(json.dumps(host_sets), 200)
    return resp


@app.route('/api/v1/hostsets', methods=['POST'])
def create_host_set():
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'name': None, 'comment': None,
                  'domain': None, 'setmembers': None}

    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)

    if 'name' in list(data.keys()):
        for host_set in host_sets['members']:
            if host_set['name'] == data['name']:
                throw_error(409, EXISTENT_SET, 'Set exists')
        if len(data['name']) > 31:
            throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                        'invalid input: string length exceeds limit')
    else:
        throw_error(400, INV_INPUT,
                    'No host set name provided.')

    host_sets['members'].append(data)
    resp = flask.make_response(
        "", 201, {'location': '/api/v1/hostsets/' + data['name']})
    return resp


@app.route('/api/v1/hostsets/<host_set_name>', methods=['GET'])
def get_host_set(host_set_name):
    debugRequest(flask.request)

    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in host_set_name:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'illegal character in input')

    for host_set in host_sets['members']:
        if host_set['name'] == host_set_name:
            resp = flask.make_response(json.dumps(host_set), 200)
            return resp

    throw_error(404, NON_EXISTENT_SET, "host set doesn't exist")


@app.route('/api/v1/hostsets/<host_set_name>', methods=['PUT'])
def modify_host_set(host_set_name):
    debugRequest(flask.request)

    if len(host_set_name) > 31:
            throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                        'invalid input: string length exceeds limit')

    data = json.loads(flask.request.data.decode('utf-8'))

    if 'newName' in data:
        if len(data['newName']) > 32:
            throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                        'host set name is too long.')
        if 'setmembers' in data:
            throw_error(400, INV_INPUT_PARAM_CONFLICT,
                        "invalid input: parameters cannot be present at the"
                        " same time")

    for host_set in host_sets['members']:
        if host_set['name'] == host_set_name:
            if 'newName' in data:
                host_set['name'] = data['newName']
            if 'comment' in data:
                host_set['comment'] = data['comment']
            if 'setmembers' in data and 'action' in data:
                members = data['setmembers']
                for member in members:
                    get_host(member)
                if 1 == data['action']:
                    # 1 is memAdd - Adds a member to the set
                    if 'setmembers' not in host_set:
                        host_set['setmembers'] = []
                    host_set['setmembers'].extend(members)
                elif 2 == data['action']:
                    # 2 is memRemove- Removes a member from the set
                    for member in members:
                        host_set['setmembers'].remove(member)
                else:
                    throw_error(400, INV_INPUT_BAD_ENUM_VALUE,
                                desc='invalid input: bad enum value - action')

        resp = flask.make_response(json.dumps(host_set), 200)
        return resp

    throw_error(404, NON_EXISTENT_SET, "host set doesn't exist")


@app.route('/api/v1/hostsets/<host_set_name>', methods=['DELETE'])
def delete_host_set(host_set_name):
    debugRequest(flask.request)

    for host_set in host_sets['members']:
        if host_set['name'] == host_set_name:
            host_sets['members'].remove(host_set)
            return flask.make_response("", 200)

    throw_error(404, NON_EXISTENT_SET,
                "The host set '%s' does not exists." % host_set_name)


# Host

@app.route('/api/v1/hosts', methods=['POST'])
def create_hosts():
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_members = ['FCWWNs', 'descriptors', 'domain', 'iSCSINames', 'id',
                     'name']

    for member_key in list(data.keys()):
        if member_key not in valid_members:
            throw_error(400, INV_INPUT,
                        "Invalid Parameter '%s'" % member_key)

    if data['name'] is None:
        throw_error(400, INV_INPUT_MISSING_REQUIRED, 'Name not specified.')

    elif len(data['name']) > 31:
        throw_error(400, INV_INPUT_EXCEEDS_LENGTH, 'Host name is too long.')

    elif 'domain' in data and len(data['domain']) > 31:
        throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                    'Domain name is too long.')

    elif 'domain' in data and data['domain'] == '':
        throw_error(400, INV_INPUT_EMPTY_STR,
                    'Input string (for domain, iSCSI etc.) is empty.')

    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in data['name']:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Error parsing host-name or domain-name')

        elif 'domain' in data and char in data['domain']:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Error parsing host-name or domain-name')

    if 'FCWWNs' in list(data.keys()):
        if 'iSCSINames' in list(data.keys()):
            throw_error(400, INV_INPUT_PARAM_CONFLICT,
                        'FCWWNS and iSCSINames are both specified.')

    if 'FCWWNs' in list(data.keys()):
        fc = data['FCWWNs']
        for wwn in fc:
            if len(wwn.replace(':', '')) != 16:
                throw_error(400, INV_INPUT_WRONG_TYPE,
                            'Length of WWN is not 16.')

    if 'FCWWNs' in data:
        for host in hosts['members']:
            if 'FCWWNs' in host:
                for fc_path in data['FCWWNs']:
                    if fc_path in host['FCWWNs']:
                        throw_error(409, EXISTENT_PATH,
                                    'WWN already claimed by other host.')

    if 'iSCSINames' in data:
        for host in hosts:
            if 'iSCSINames' in host:
                for iqn in data['iSCSINames']:
                    if iqn in host['iSCSINames']:
                        throw_error(409, EXISTENT_PATH,
                                    'iSCSI name already claimed by other'
                                    ' host.')

    for host in hosts['members']:
        if data['name'] == host['name']:
            throw_error(409, EXISTENT_HOST,
                        "HOST '%s' already exist." % data['name'])

    hosts['members'].append(data)
    hosts['total'] = hosts['total'] + 1

    resp = flask.make_response("", 201)
    return resp


@app.route('/api/v1/hosts/<host_name>', methods=['PUT'])
def modify_host(host_name):
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    if host_name == 'None':
        throw_error(404, INV_INPUT, 'Missing host name.')

    if 'FCWWNs' in list(data.keys()):
        if 'iSCSINames' in list(data.keys()):
            throw_error(400, INV_INPUT_PARAM_CONFLICT,
                        'FCWWNS and iSCSINames are both specified.')
        elif 'pathOperation' not in list(data.keys()):
            throw_error(400, INV_INPUT_ONE_REQUIRED,
                        'pathOperation is missing and WWN is specified.')

    if 'iSCSINames' in list(data.keys()):
        if 'pathOperation' not in list(data.keys()):
            throw_error(400, INV_INPUT_ONE_REQUIRED,
                        'pathOperation is missing and iSCSI Name is'
                        ' specified.')

    if 'newName' in list(data.keys()):
        charset = {'!', '@', '#', '$', '%', '&', '^'}
        for char in charset:
            if char in data['newName']:
                throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                            'Error parsing host-name or domain-name')
        if len(data['newName']) > 32:
            throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                        'New host name is too long.')
        for host in hosts['members']:
            if host['name'] == data['newName']:
                throw_error(409, EXISTENT_HOST,
                            'New host name is already used.')

    if 'pathOperation' in list(data.keys()):
        if 'iSCSINames' in list(data.keys()):
            for host in hosts['members']:
                if host['name'] == host_name:
                    if data['pathOperation'] == 1:
                        for host in hosts['members']:
                            if 'iSCSINames' in list(host.keys()):
                                for path in data['iSCSINames']:
                                    for h_paths in host['iSCSINames']:
                                        if path == h_paths:
                                            throw_error(409, EXISTENT_PATH,
                                                        'iSCSI name is already'
                                                        ' claimed by other '
                                                        'host.')
                        for path in data['iSCSINames']:
                            host['iSCSINames'].append(path)
                        resp = flask.make_response(json.dumps(host), 200)
                        return resp
                    elif data['pathOperation'] == 2:
                        for path in data['iSCSINames']:
                            for h_paths in host['iSCSINames']:
                                if path == h_paths:
                                    host['iSCSINames'].remove(h_paths)
                                    resp = flask.make_response(
                                        json.dumps(host), 200)
                                    return resp
                            throw_error(404, NON_EXISTENT_PATH,
                                        'Removing a non-existent path.')
                    else:
                        throw_error(400, INV_INPUT_BAD_ENUM_VALUE,
                                    'pathOperation: Invalid enum value.')
            throw_error(404, NON_EXISTENT_HOST,
                        'Host to be modified does not exist.')
        elif 'FCWWNs' in list(data.keys()):
            for host in hosts['members']:
                if host['name'] == host_name:
                    if data['pathOperation'] == 1:
                        for host in hosts['members']:
                            if 'FCWWNs' in list(host.keys()):
                                for path in data['FCWWNs']:
                                    for h_paths in host['FCWWNs']:
                                        if path == h_paths:
                                            throw_error(409, EXISTENT_PATH,
                                                        'WWN is already '
                                                        'claimed by other '
                                                        'host.')
                        for path in data['FCWWNs']:
                            host['FCWWNs'].append(path)
                        resp = flask.make_response(json.dumps(host), 200)
                        return resp
                    elif data['pathOperation'] == 2:
                        for path in data['FCWWNs']:
                            for h_paths in host['FCWWNs']:
                                if path == h_paths:
                                    host['FCWWNs'].remove(h_paths)
                                    resp = flask.make_response(
                                        json.dumps(host), 200)
                                    return resp
                            throw_error(404, NON_EXISTENT_PATH,
                                        'Removing a non-existent path.')
                    else:
                        throw_error(400, INV_INPUT_BAD_ENUM_VALUE,
                                    'pathOperation: Invalid enum value.')
            throw_error(404, NON_EXISTENT_HOST,
                        'Host to be modified does not exist.')
        else:
            throw_error(400, INV_INPUT_ONE_REQUIRED,
                        'pathOperation specified and no WWNs or iSCSNames'
                        ' specified.')

    for host in hosts['members']:
        if host['name'] == host_name:
            for member_key in list(data.keys()):
                if member_key == 'newName':
                    host['name'] = data['newName']
                else:
                    host[member_key] = data[member_key]
            resp = flask.make_response(json.dumps(host), 200)
            return resp

    throw_error(404, NON_EXISTENT_HOST,
                'Host to be modified does not exist.')


@app.route('/api/v1/hosts/<host_name>', methods=['DELETE'])
def delete_host(host_name):
    debugRequest(flask.request)

    # Can't delete a host with VLUN
    if len(get_vluns_for_host(host_name)) > 0:
        throw_error(409, EXPORTED_VLUN, "has exported VLUN")

    # Can't delete a host in a host set
    if get_host_set_for_host(host_name) is not None:
        throw_error(409, HOST_IN_SET, "host is a member of a set")

    for host in hosts['members']:
        if host['name'] == host_name:
            hosts['members'].remove(host)
            return flask.make_response("", 200)

    throw_error(404, NON_EXISTENT_HOST,
                "The host '%s' doesn't exist" % host_name)


@app.route('/api/v1/hosts', methods=['GET'])
def get_hosts():
    debugRequest(flask.request)
    query = flask.request.args.get('query')
    matched_hosts = []
    if query is not None:
        parsed_query = _parse_query(query)
        for host in hosts['members']:
            pprint.pprint(host)
            if 'FCWWNs' in host:
                pprint.pprint(host['FCWWNs'])
                for hostwwn in host['FCWWNs']:
                    if hostwwn.replace(':', '') in parsed_query['wwns']:
                        matched_hosts.append(host)
                        break
            elif 'iSCSINames' in host:
                pprint.pprint(host['iSCSINames'])
                for iqn in host['iSCSINames']:
                    if iqn in parsed_query['iqns']:
                        matched_hosts.append(host)
                        break

        result = {'total': len(matched_hosts), 'members': matched_hosts}
        resp = flask.make_response(json.dumps(result), 200)
    else:
        resp = flask.make_response(json.dumps(hosts), 200)
    return resp


def _parse_query(query):
    wwns = re.findall("wwn==([0-9A-Z]*)", query)
    iqns = re.findall("name==([\w.:-]*)", query)
    parsed_query = {"wwns": wwns, "iqns": iqns}
    return parsed_query


@app.route('/api/v1/hosts/<host_name>', methods=['GET'])
def get_host(host_name):
    debugRequest(flask.request)
    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in host_name:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Host name contains invalid character.')

    if host_name == 'InvalidURI':
        throw_error(400, INV_INPUT, 'Invalid URI Syntax.')

    for host in hosts['members']:
        if host['name'] == host_name:

            if 'iSCSINames' in list(host.keys()):
                iscsi_paths = []
                for path in host['iSCSINames']:
                    iscsi_paths.append({'name': path})
                host['iSCSIPaths'] = iscsi_paths

            elif 'FCWWNs' in list(host.keys()):
                fc_paths = []
                for path in host['FCWWNs']:
                    fc_paths.append({'wwn': path.replace(':', '')})
                host['FCPaths'] = fc_paths

            resp = flask.make_response(json.dumps(host), 200)
            return resp

    throw_error(404, NON_EXISTENT_HOST, "host does not exist")

# Port


@app.route('/api/v1/ports', methods=['GET'])
def get_ports():
    debugRequest(flask.request)
    resp = flask.make_response(json.dumps(ports), 200)
    return resp

# VLUN


@app.route('/api/v1/vluns', methods=['POST'])
def create_vluns():
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'volumeName': None, 'lun': 0, 'hostname': None,
                  'portPos': None,
                  'noVcn': False, 'overrideLowerPriority': False}

    valid_port_keys = {'node': 1, 'slot': 1, 'cardPort': 0}

    # do some fake errors here depending on data
    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)
        elif 'portPos' in list(data.keys()):
            portP = data['portPos']
            for subkey in list(portP.keys()):
                if subkey not in valid_port_keys:
                    throw_error(400, INV_INPUT,
                                "Invalid Parameter '%s'" % subkey)

    if 'lun' in data:
        if data['lun'] > 16384:
            throw_error(400, TOO_LARGE, 'LUN is greater than 16384.')
    else:
        throw_error(400, INV_INPUT, 'Missing LUN.')

    if 'volumeName' not in data:
        throw_error(400, INV_INPUT_MISSING_REQUIRED, 'Missing volumeName.')
    else:
        for volume in volumes['members']:
            if volume['name'] == data['volumeName']:
                vluns['members'].append(data)
                resp = flask.make_response(json.dumps(vluns), 201)
                resp.headers['location'] = '/api/v1/vluns/'
                return resp
        throw_error(404, NON_EXISTENT_VOL,
                    'Specified volume does not exist.')


@app.route('/api/v1/vluns/<vlun_str>', methods=['DELETE'])
def delete_vluns(vlun_str):
    # <vlun_str> is like volumeName,lun,host,node:slot:port
    debugRequest(flask.request)

    params = vlun_str.split(',')
    for vlun in vluns['members']:
        if vlun['volumeName'] == params[0] and vlun['lun'] == int(params[1]):
            if len(params) == 4:
                if str(params[2]) != vlun['hostname']:
                    throw_error(404, NON_EXISTENT_HOST,
                                "The host '%s' doesn't exist" % params[2])

                print(vlun['portPos'])
                port = getPort(vlun['portPos'])
                if not port == params[3]:
                    throw_error(400, INV_INPUT_PORT_SPECIFICATION,
                                "Specified port is invalid %s" % params[3])

            elif len(params) == 3:
                if ':' in params[2]:
                    port = getPort(vlun['portPos'])
                    if not port == params[2]:
                        throw_error(400, INV_INPUT_PORT_SPECIFICATION,
                                    "Specified port is invalid %s" % params[2])

                else:
                    if str(params[2]) != vlun['hostname']:
                        throw_error(404, NON_EXISTENT_HOST,
                                    "The host '%s' doesn't exist" % params[2])

            vluns['members'].remove(vlun)
            return flask.make_response(json.dumps(params), 200)

    throw_error(404, NON_EXISTENT_VLUN,
                "The volume '%s' doesn't exist" % vluns)


def getPort(portPos):
    port = "%s:%s:%s" % (portPos['node'], portPos['slot'], portPos['cardPort'])
    print(port)
    return port


@app.route('/api/v1/vluns', methods=['GET'])
def get_vluns():
    debugRequest(flask.request)
    resp = flask.make_response(json.dumps(vluns), 200)
    return resp


def get_vluns_for_host(host_name):
    ret = []
    for vlun in vluns['members']:
        if vlun['hostname'] == host_name:
            ret.append(vlun)
    return ret


# VOLUMES & SNAPSHOTS

@app.route('/api/v1/volumes/<volume_name>', methods=['POST'])
def create_snapshot(volume_name):
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))
    # is this for an online copy?
    onlineCopy = False

    valid_keys = {'action': None, 'parameters': None}
    valid_parm_keys = {'name': None, 'destVolume': None, 'destCPG': None,
                       'id': None, 'comment': None, 'online': None,
                       'readOnly': None, 'expirationHours': None,
                       'retentionHours': None}

    # do some fake errors here depending on data
    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)
        elif 'parameters' in list(data.keys()):
            parm = data['parameters']
            for subkey in list(parm.keys()):
                if subkey not in valid_parm_keys:
                    throw_error(400, INV_INPUT,
                                "Invalid Parameter '%s'" % subkey)

    if 'action' in data and data['action'] == 'createPhysicalCopy':
        valid_offline_param_keys = {'online': None, 'destVolume': None,
                                    'saveSnapshot': None,
                                    'priority': None}
        valid_online_param_keys = {'online': None, 'destCPG': None,
                                   'tpvv': None, 'tdvv': None,
                                   'snapCPG': None, 'saveSnapshot': None,
                                   'priority': None}
        params = data['parameters']
        if 'online' in params and params['online']:
            # we are checking online copy
            onlineCopy = True
            for subkey in params.keys():
                if subkey not in valid_online_param_keys:
                    throw_error(400, INV_INPUT,
                                "Invalid Parameter '%s'" % subkey)
        else:
            # we are checking offline copy
            for subkey in params.keys():
                if subkey not in valid_offline_param_keys:
                    throw_error(400, INV_INPUT,
                                "Invalid Parameter '%s'" % subkey)

    for volume in volumes['members']:
        if volume['name'] == volume_name:
            if data['action'] == "createPhysicalCopy":
                new_name = data['parameters'].get('destVolume')
                if not onlineCopy:
                    # we have to have the destination volume for offline copies
                    found = False
                    for vol in volumes['members']:
                        if vol['name'] == new_name:
                            found = True
                            break

                    if not found:
                        throw_error(404, NON_EXISTENT_VOL,
                                    "volume does not exist")

            else:
                new_name = data['parameters'].get('name')

            volumes['members'].append({'name': new_name})

            resp = flask.make_response(json.dumps(volume), 200)
            return resp

    throw_error(404, NON_EXISTENT_VOL, "volume doesn't exist")


@app.route('/api/v1/volumesets/<volumeset_name>', methods=['POST'])
def create_volumeset_snapshot(volumeset_name):
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'action': None, 'parameters': None}
    valid_parm_keys = {'name': None, 'destVolume': None, 'destCPG': None,
                       'id': None, 'comment': None, 'online': None,
                       'readOnly': None, 'expirationHours': None,
                       'retentionHours': None}

    # do some fake errors here depending on data
    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)
        elif 'parameters' in list(data.keys()):
            parm = data['parameters']
            for subkey in list(parm.keys()):
                if subkey not in valid_parm_keys:
                    throw_error(400, INV_INPUT,
                                "Invalid Parameter '%s'" % subkey)

    vvset_snap_name = data['parameters']['name']
    snap_base = vvset_snap_name.split("@count@")[0]

    for vset in volume_sets['members']:
        setmembers = vset.get('setmembers', None)
        if vset['name'] == volumeset_name and setmembers:
            for i, member in enumerate(setmembers):
                vol_name = snap_base + str(i)
                volumes['members'].append({'name': vol_name, 'copyOf': member})
            if data['action'] == "createPhysicalCopy":
                new_name = data['parameters'].get('destVolume')
            else:
                new_name = data['parameters'].get('name')

            volume_sets['members'].append({'name': new_name})

            resp = flask.make_response(json.dumps(vset), 200)
            return resp

    throw_error(404, NON_EXISTENT_SET, "volume set doesn't exist")


@app.route('/api/v1/volumes', methods=['POST'])
def create_volumes():
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'name': None, 'cpg': None, 'sizeMiB': None, 'id': None,
                  'comment': None, 'policies': None, 'snapCPG': None,
                  'ssSpcAllocWarningPct': None, 'ssSpcAllocLimitPct': None,
                  'tpvv': None, 'usrSpcAllocWarningPct': None,
                  'usrSpcAllocLimitPct': None, 'isCopy': None,
                  'copyOfName': None, 'copyRO': None, 'expirationHours': None,
                  'retentionHours': None}

    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)

    if 'name' in list(data.keys()):
        for vol in volumes['members']:
            if vol['name'] == data['name']:
                throw_error(409, EXISTENT_VOL,
                            'The volume already exists.')
        if len(data['name']) > 31:
            throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                        'Invalid Input: String length exceeds limit : Name')
    else:
        throw_error(400, INV_INPUT,
                    'No volume name provided.')

    if 'sizeMiB' in list(data.keys()):
        if data['sizeMiB'] < 256:
            throw_error(400, INV_INPUT_EXCEEDS_RANGE,
                        'Minimum volume size is 256 MiB')
        elif data['sizeMiB'] > 16777216:
            throw_error(400, TOO_LARGE,
                        'Volume size is above architectural limit : 16TiB')

    if 'id' in list(data.keys()):
        for vol in volumes['members']:
            if vol['id'] == data['id']:
                throw_error(409, EXISTENT_ID,
                            'Specified volume ID already exists.')

    volumes['members'].append(data)
    return flask.make_response("", 200)


@app.route('/api/v1/volumes/<volume_name>', methods=['DELETE'])
def delete_volumes(volume_name):
    debugRequest(flask.request)

    for volume in volumes['members']:
        if volume['name'] == volume_name:
            volumes['members'].remove(volume)
            return flask.make_response("", 200)

    throw_error(404, NON_EXISTENT_VOL,
                "The volume '%s' does not exists." % volume_name)


@app.route('/api/v1/volumes', methods=['GET'])
def get_volumes():
    debugRequest(flask.request)
    resp = flask.make_response(json.dumps(volumes), 200)
    return resp


@app.route('/api/v1/volumes/<volume_name>', methods=['GET'])
def get_volume(volume_name):
    debugRequest(flask.request)

    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in volume_name:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Invalid character for volume name.')

    for volume in volumes['members']:
        if volume['name'] == volume_name:
            resp = flask.make_response(json.dumps(volume), 200)
            return resp

    throw_error(404, NON_EXISTENT_VOL, "volume doesn't exist")


@app.route('/api/v1/volumes/<volume_name>', methods=['PUT'])
def modify_volume(volume_name):
    debugRequest(flask.request)

    if volume_name not in [volume['name'] for volume in volumes['members']]:
        throw_error(404, NON_EXISTENT_VOL, "The volume does not exist")

    for volume in volumes['members']:
        if volume['name'] == volume_name:
            break

    data = json.loads(flask.request.data.decode('utf-8'))
    _grow_volume(volume, data)

    # do volume renames last
    if 'newName' in data:
        volume['name'] = data['newName']

    resp = flask.make_response(json.dumps(volume), 200)
    return resp


def _grow_volume(volume, data):
    # Only grow if there is a need
    if 'sizeMiB' in data:
        size = data['sizeMiB']
        if size <= 0:
            throw_error(400, INV_INPUT_VV_GROW_SIZE, 'Invalid grow size')

        cur_size = volume['sizeMiB']
        new_size = cur_size + size
        if new_size > 16777216:
            throw_error(403, VV_NEW_SIZE_EXCEED_CPG_LIMIT,
                        'New volume size exceeds CPG limit.')
        volume['sizeMiB'] = new_size


@app.route('/api/v1/remotecopygroups', methods=['GET'])
def get_remote_copy_groups():
    debugRequest(flask.request)
    resp = flask.make_response(json.dumps(remote_copy_groups), 200)
    return resp


@app.route('/api/v1/remotecopygroups/<rcg_name>', methods=['GET'])
def get_remote_copy_group(rcg_name):
    debugRequest(flask.request)

    for rcg in remote_copy_groups['members']:
        if rcg['name'] == rcg_name:
            resp = flask.make_response(json.dumps(rcg), 200)
            return resp

    throw_error(404, NON_EXISTENT_RCOPY_GROUP,
                "remote copy group doesn't exist")


@app.route('/api/v1/remotecopygroups', methods=['POST'])
def create_remote_copy_group():
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'name': None, 'targets': None, 'targetName': None,
                  'mode': None, 'userCPG': None, 'snapCPG': None,
                  'localSnapCPG': None, 'localUserCPG': None, 'domain': None}

    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)

    if 'name' in list(data.keys()):
        for rcg in remote_copy_groups['members']:
            if rcg['name'] == data['name']:
                throw_error(409, EXISTENT_RCOPY_GROUP,
                            "Remote copy group exists.")
        if len(data['name']) > 25:
            throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                        'Invalid Input: String length exceeds limit : Name')
    else:
        throw_error(400, INV_INPUT,
                    'No remote copy group provided.')

    data['volumes'] = []
    remote_copy_groups['members'].append(data)
    return flask.make_response("", 200)


@app.route('/api/v1/remotecopygroups/<rcg_name>', methods=['DELETE'])
def delete_remote_copy_group(rcg_name):
    debugRequest(flask.request)
    for rcg in remote_copy_groups['members']:
        if rcg['name'] == rcg_name:
            remote_copy_groups['members'].remove(rcg)
            return flask.make_response("", 200)

    throw_error(404, NON_EXISTENT_RCOPY_GROUP,
                "The remote copy group '%s' does not exist." % rcg_name)


@app.route('/api/v1/remotecopygroups/<rcg_name>', methods=['PUT'])
def modify_remote_copy_group(rcg_name):
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'targets': None, 'targetName': None,
                  'mode': None, 'userCPG': None, 'snapCPG': None,
                  'localSnapCPG': None, 'localUserCPG': None, 'domain': None,
                  'unsetUserCPG': None, 'unsetSnapCPG': None, '': None,
                  'remoteUserCPG': None, 'remoteSnapCPG': None,
                  'syncPeriod': None, 'rmSyncPeriod': None,
                  'snapFrequency': None, 'rmSnapFrequency': None,
                  'policies': None, 'autoRecover': None,
                  'overPeriodAlert': None, 'autoFailover': None,
                  'pathManagement': None, 'secVolumeName': None,
                  'snapshotName': None, 'volumeAutoCreation': None,
                  'skipInitialSync': None, 'volumeName': None, 'action': None}

    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)

    action = data.get('action')
    for rcg in remote_copy_groups['members']:
        if rcg['name'] == rcg_name:
            # We are modifying values for a remote copy group
            if not action:
                for k, v in data.items():
                    rcg[k] = v
                    resp = flask.make_response(json.dumps(rcg), 200)
            # We are adding a volume to a remote copy group
            elif action == ADMIT_VV:
                vol_found = False
                for vol in volumes['members']:
                    if data['volumeName'] == vol['name']:
                        vol_found = True
                        rcg['volumes'].append(vol)
                if not vol_found:
                    throw_error(404, NON_EXISTENT_VOL, "volume doesn't exist")

                resp = flask.make_response(json.dumps(rcg), 200)
            # We are removing a volume to a remote copy group
            elif action == DISMISS_VV:
                for vol in rcg['volumes']:
                    if data['volumeName'] == vol['name']:
                        rcg['volumes'].remove(vol)
                resp = flask.make_response(json.dumps(rcg), 200)
            # We are starting remote copy on a group
            elif action == START_GROUP:
                targets = rcg['targets']
                for target in targets:
                    target['state'] = RCOPY_STARTED
                resp = flask.make_response(json.dumps(rcg), 200)
            # We are stopping remote copy on a group
            elif action == STOP_GROUP:
                targets = rcg['targets']
                for target in targets:
                    target['state'] = RCOPY_STOPPED
                resp = flask.make_response(json.dumps(rcg), 200)
            # We are synchronizing the remote copy group
            elif action == SYNC_GROUP:
                targets = rcg['targets']
                sync_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                for target in targets:
                    target['groupLastSyncTime'] = sync_time
                resp = flask.make_response(json.dumps(rcg), 200)

            return resp

    throw_error(404, NON_EXISTENT_RCOPY_GROUP,
                "remote copy group doesn't exist")


@app.route('/api/v1/remotecopygroups/<rcg_name>', methods=['POST'])
def recover_remote_copy_group(rcg_name):
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'targets': None, 'targetName': None, 'skipStart': None,
                  'skipSync': None, 'discardNewData': None,
                  'skipPromote': None, 'noSnapshot': None, 'stopGroups': None,
                  'localGroupsDirection': None, 'action': None}

    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)

    action = data.get('action')
    for rcg in remote_copy_groups['members']:
        if rcg['name'] == rcg_name:
            # We are failing over a remote copy group
            if action == FAILOVER_GROUP:
                rcg['roleReversed'] = True
                resp = flask.make_response(json.dumps(rcg), 200)

    return resp

    throw_error(404, NON_EXISTENT_RCOPY_GROUP,
                "remote copy group doesn't exist")


@app.route('/api/v1/volumesets', methods=['GET'])
def get_volume_sets():
    debugRequest(flask.request)
    resp = flask.make_response(json.dumps(volume_sets), 200)
    return resp


@app.route('/api/v1/volumesets', methods=['POST'])
def create_volume_set():
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))

    valid_keys = {'name': None, 'comment': None,
                  'domain': None, 'setmembers': None}

    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)

    if 'name' in list(data.keys()):
        for vset in volume_sets['members']:
            if vset['name'] == data['name']:
                throw_error(409, EXISTENT_SET, "Set exists")
        if len(data['name']) > 31:
            throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                        'Invalid Input: String length exceeds limit : Name')
    else:
        throw_error(400, INV_INPUT,
                    'No volume set name provided.')

    volume_sets['members'].append(data)
    return flask.make_response("", 200)


@app.route('/api/v1/volumesets/<volume_set_name>', methods=['GET'])
def get_volume_set(volume_set_name):
    debugRequest(flask.request)

    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in volume_set_name:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Invalid character for volume set name.')

    for vset in volume_sets['members']:
        if vset['name'] == volume_set_name:
            resp = flask.make_response(json.dumps(vset), 200)
            return resp

    throw_error(404, NON_EXISTENT_SET, "volume set doesn't exist")


@app.route('/api/v1/volumesets/<volume_set_name>', methods=['PUT'])
def modify_volume_set(volume_set_name):
    debugRequest(flask.request)
    data = json.loads(flask.request.data.decode('utf-8'))
    for vset in volume_sets['members']:
        if vset['name'] == volume_set_name:
            if 'newName' in data:
                vset['name'] = data['newName']
            if 'comment' in data:
                vset['comment'] = data['comment']
            if 'flashCachePolicy' in data:
                vset['flashCachePolicy'] = data['flashCachePolicy']
            if 'setmembers' in data and 'action' in data:
                members = data['setmembers']
                if 1 == data['action']:
                    # 1 is memAdd - Adds a member to the set
                    if 'setmembers' not in vset:
                        vset['setmembers'] = []
                    vset['setmembers'].extend(members)
                elif 2 == data['action']:
                    # 2 is memRemove- Removes a member from the set
                    for member in members:
                        vset['setmembers'].remove(member)
                else:
                    throw_error(400, INV_INPUT_BAD_ENUM_VALUE,
                                desc='invalid input: bad enum value - action')

        resp = flask.make_response(json.dumps(vset), 200)
        return resp

    throw_error(404, NON_EXISTENT_SET, "volume set doesn't exist")


@app.route('/api/v1/volumesets/<volume_set_name>', methods=['DELETE'])
def delete_volume_set(volume_set_name):
    debugRequest(flask.request)
    for vset in volume_sets['members']:
        if vset['name'] == volume_set_name:
            volume_sets['members'].remove(vset)
            if 'qos' in vset:
                try:
                    _delete_qos_db(vset['qos'])
                except Exception as ex:
                    print(vars(ex))
            return flask.make_response("", 200)

    throw_error(404, NON_EXISTENT_SET,
                "The volume set '%s' does not exists." % volume_set_name)


def _validate_qos_input(data):
    valid_keys = {'name': None, 'type': None,
                  'priority': None,
                  'bwMinGoalKB': None,
                  'bwMaxLimitKB': None,
                  'ioMinGoal': None,
                  'ioMaxLimit': None,
                  'enable': None,
                  'bwMinGoalOP': None,
                  'bwMaxLimitOP': None,
                  'ioMinGoalOP': None,
                  'ioMaxLimitOP': None,
                  'latencyGoal': None,
                  'defaultLatency': None}

    for key in list(data.keys()):
        if key not in list(valid_keys.keys()):
            throw_error(400, INV_INPUT, "Invalid Parameter '%s'" % key)


@app.route('/api/v1/qos', methods=['GET'])
def query_all_qos():
    debugRequest(flask.request)
    return flask.make_response(json.dumps(qos_db), 200)


@app.route('/api/v1/qos/<target_type>:<target_name>', methods=['GET'])
def query_qos(target_type, target_name):
    debugRequest(flask.request)
    qos = _get_qos_db(target_name)
    return flask.make_response(json.dumps(qos))


def _get_qos_db(name):
    for qos in qos_db['members']:
        if qos['name'] == name:
            return qos

    throw_error(404, NON_EXISTENT_QOS_RULE, "non-existent QoS rule")


def debug_qos(title):
    if debugRequest:
        print(title)
        pprint.pprint(qos_db)


def _add_qos_db(qos):
    debug_qos("_add_qos_db start")
    qos['id'] = uuid.uuid1().urn
    qos_db['members'].append(qos)
    qos_db['total'] = len(qos_db['members'])
    debug_qos("_add_qos_db end")
    return qos['id']


def _modify_qos_db(qos_id, new_qos):
    debug_qos("_modify_qos_db start")
    for qos in qos_db['members']:
        if qos['id'] == qos_id:
            qos.update(new_qos)
            debug_qos("_modify_qos_db end")
            return

    debug_qos("_modify_qos_db end error")
    throw_error(404, NON_EXISTENT_QOS_RULE, "non-existent QoS rule")


def _delete_qos_db(qos_id):
    debug_qos("_delete_qos_db start")
    for qos in qos_db['members']:
        if qos['id'] == qos_id:
            qos_db['members'].remove(qos)

    debug_qos("_delete_qos_db end")


@app.route('/api/v1/qos', methods=['POST'])
def create_qos():
    debugRequest(flask.request)
    qos = json.loads(flask.request.data.decode('utf-8'))

    if 'name' not in qos:
        throw_error(404, INV_INPUT, "Missing required parameter 'name'")

    if 'type' not in qos:
        throw_error(404, INV_INPUT, "Missing required parameter 'type'")
    elif qos['type'] != 1:
        throw_error(404, INV_INPUT,
                    "Flask currently only supports type = 1 (VVSET). "
                    "Type unsuppored: %s" % qos['type'])
    _validate_qos_input(qos)

    for vset in volume_sets['members']:
        if vset['name'] == qos['name']:
            if 'qos' in vset:
                throw_error(400, EXISTENT_QOS_RULE, "QoS rule exists")
            else:
                qos_id = _add_qos_db(qos)
                vset['qos'] = qos_id
                return flask.make_response("", 201)

    throw_error(404, INV_INPUT_QOS_TARGET_OBJECT, "Invalid QOS target object")


@app.route('/api/v1/qos/<target_type>:<name>', methods=['PUT'])
def modify_qos(target_type, name):
    debugRequest(flask.request)
    qos = json.loads(flask.request.data.decode('utf-8'))
    _validate_qos_input(qos)

    for vset in volume_sets['members']:
        if vset['name'] == name:
            if 'qos' not in vset:
                throw_error(404, NON_EXISTENT_QOS_RULE,
                            "non-existent QoS rule")
            else:
                _modify_qos_db(vset['qos'], qos)
                return flask.make_response("", 200)

    throw_error(404, INV_INPUT_QOS_TARGET_OBJECT, "Invalid QOS target object")


@app.route('/api/v1/qos/<target_type>:<target_name>', methods=['DELETE'])
def delete_qos(target_type, target_name):
    debugRequest(flask.request)

    for vset in volume_sets['members']:
        if vset['name'] == target_name:
            if 'qos' not in vset:
                throw_error(404, NON_EXISTENT_SET, "QoS rule does not exists")
            else:
                _delete_qos_db(vset['qos'])
                return flask.make_response("", 200)

    throw_error(404, INV_INPUT_QOS_TARGET_OBJECT, "Invalid QOS target object")


@app.route('/api/v1/wsapiconfiguration', methods=['GET'])
def get_wsapi_configuration():
    debugRequest(flask.request)
    # TODO: these are copied from the pdf
    config = {"httpState": "Enabled",
              "httpPort": 8008,
              "httpsState": "Enabled",
              "httpsPort": 8080,
              "version": "1.3",
              "sessionsInUse": 0,
              "systemResourceUsage": 144}

    return flask.make_response(json.dumps(config))


@app.route('/api/v1/system', methods=['GET'])
def get_system():
    debugRequest(flask.request)

    system_info = {"id": 12345,
                   "name": "Flask",
                   "systemVersion": "3.2.1.46",
                   "IPv4Addr": "10.10.10.10",
                   "model": "HP_3PAR 7400",
                   "serialNumber": "1234567",
                   "totalNodes": 2,
                   "masterNode": 0,
                   "onlineNodes": [0, 1],
                   "clusterNodes": [0, 1],
                   "chunkletSizeMiB": 1024,
                   "totalCapacityMiB": 35549184.0,
                   "allocatedCapacityMiB": 4318208.0,
                   "freeCapacityMiB": 31230976.0,
                   "failedCapacityMiB": 0.0,
                   "location": "Flask Test Virtual",
                   "owner": "Flask Owner",
                   "contact": "flask@flask.com",
                   "comment": "flask test env",
                   "timeZone": "America/Los_Angeles"}

    resp = flask.make_response(json.dumps(system_info), 200)
    return resp


@app.route('/api/v1/capacity', methods=['GET'])
def get_overall_capacity():
    debugRequest(flask.request)

    capacity_info = {
        "allCapacity": {
            "totalMiB": 20054016,
            "allocated": {
                "totalAllocatedMiB": 12535808,
                "volumes": {
                    "totalVolumesMiB": 10919936,
                    "nonCPGsMiB": 0,
                    "nonCPGUserMiB": 0,
                    "nonCPGSnapshotMiB": 0,
                    "nonCPGAdminMiB": 0,
                    "CPGsMiB": 10919936,
                    "CPGUserMiB": 7205538,
                    "CPGUserUsedMiB": 7092550,
                    "CPGUserUnusedMiB": 112988,
                    "CPGSnapshotMiB": 2411870,
                    "CPGSnapshotUsedMiB": 210256,
                    "CPGSnapshotUnusedMiB": 2201614,
                    "CPGAdminMiB": 1302528,
                    "CPGAdminUsedMiB": 115200,
                    "CPGAdminUnusedMiB": 1187328,
                    "unmappedMiB": 0
                },
                "system": {
                    "totalSystemMiB": 1615872,
                    "internalMiB": 780288,
                    "spareMiB": 835584,
                    "spareUsedMiB": 0,
                    "spareUnusedMiB": 835584
                }
            },
            "freeMiB": 7518208,
            "freeInitializedMiB": 7518208,
            "freeUninitializedMiB": 0,
            "unavailableCapacityMiB": 0,
            "failedCapacityMiB": 0
        },
        "FCCapacity": {
            "totalMiB": 20054016,
            "allocated": {
                "totalAllocatedMiB": 12535808,
                "volumes": {
                    "totalVolumesMiB": 10919936,
                    "nonCPGsMiB": 0,
                    "nonCPGUserMiB": 0,
                    "nonCPGSnapshotMiB": 0,
                    "nonCPGAdminMiB": 0,
                    "CPGsMiB": 10919936,
                    "CPGUserMiB": 7205538,
                    "CPGUserUsedMiB": 7092550,
                    "CPGUserUnusedMiB": 112988,
                    "CPGSnapshotMiB": 2411870,
                    "CPGSnapshotUsedMiB": 210256,
                    "CPGSnapshotUnusedMiB": 2201614,
                    "CPGAdminMiB": 1302528,
                    "CPGAdminUsedMiB": 115200,
                    "CPGAdminUnusedMiB": 1187328,
                    "unmappedMiB": 0
                },
                "system": {
                    "totalSystemMiB": 1615872,
                    "internalMiB": 780288,
                    "spareMiB": 835584,
                    "spareUsedMiB": 0,
                    "spareUnusedMiB": 835584
                }
            },
            "freeMiB": 7518208,
            "freeInitializedMiB": 7518208,
            "freeUninitializedMiB": 0,
            "unavailableCapacityMiB": 0,
            "failedCapacityMiB": 0
        },
        "NLCapacity": {
            "totalMiB": 0,
            "allocated": {
                "totalAllocatedMiB": 0,
                "volumes": {
                    "totalVolumesMiB": 0,
                    "nonCPGsMiB": 0,
                    "nonCPGUserMiB": 0,
                    "nonCPGSnapshotMiB": 0,
                    "nonCPGAdminMiB": 0,
                    "CPGsMiB": 0,
                    "CPGUserMiB": 0,
                    "CPGUserUsedMiB": 0,
                    "CPGUserUnusedMiB": 0,
                    "CPGSnapshotMiB": 0,
                    "CPGSnapshotUsedMiB": 0,
                    "CPGSnapshotUnusedMiB": 0,
                    "CPGAdminMiB": 0,
                    "CPGAdminUsedMiB": 0,
                    "CPGAdminUnusedMiB": 0,
                    "unmappedMiB": 0
                },
                "system": {
                    "totalSystemMiB": 0,
                    "internalMiB": 0,
                    "spareMiB": 0,
                    "spareUsedMiB": 0,
                    "spareUnusedMiB": 0
                }
            },
            "freeMiB": 0,
            "freeInitializedMiB": 0,
            "freeUninitializedMiB": 0,
            "unavailableCapacityMiB": 0,
            "failedCapacityMiB": 0
        },
        "SSDCapacity": {
            "totalMiB": 0,
            "allocated": {
                "totalAllocatedMiB": 0,
                "volumes": {
                    "totalVolumesMiB": 0,
                    "nonCPGsMiB": 0,
                    "nonCPGUserMiB": 0,
                    "nonCPGSnapshotMiB": 0,
                    "nonCPGAdminMiB": 0,
                    "CPGsMiB": 0,
                    "CPGUserMiB": 0,
                    "CPGUserUsedMiB": 0,
                    "CPGUserUnusedMiB": 0,
                    "CPGSnapshotMiB": 0,
                    "CPGSnapshotUsedMiB": 0,
                    "CPGSnapshotUnusedMiB": 0,
                    "CPGAdminMiB": 0,
                    "CPGAdminUsedMiB": 0,
                    "CPGAdminUnusedMiB": 0,
                    "unmappedMiB": 0
                },
                "system": {
                    "totalSystemMiB": 0,
                    "internalMiB": 0,
                    "spareMiB": 0,
                    "spareUsedMiB": 0,
                    "spareUnusedMiB": 0
                }
            },
            "freeMiB": 0,
            "freeInitializedMiB": 0,
            "freeUninitializedMiB": 0,
            "unavailableCapacityMiB": 0,
            "failedCapacityMiB": 0
        },
    }

    resp = flask.make_response(json.dumps(capacity_info), 200)
    return resp


@app.route('/api', methods=['GET'])
def get_version():
    debugRequest(flask.request)
    version = {'major': 1,
               'minor': 3,
               'build': 30201256}
    resp = flask.make_response(json.dumps(version), 200)
    return resp


@app.route('/api/v1/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    debugRequest(flask.request)

    try:
        task_id = int(task_id)
    except ValueError:
        throw_error(400, INV_INPUT_WRONG_TYPE, "Task ID is not an integer")

    if task_id <= 0:
        throw_error(400, INV_INPUT_BELOW_RANGE,
                    "Task ID must be a positive value")
    if task_id > 65535:
        throw_error(400, INV_INPUT_EXCEEDS_RANGE, "Task ID is too large")

    for task in tasks['members']:
        if task['id'] == task_id:
            return flask.make_response(json.dumps(task), 200)

    throw_error(404, NON_EXISTENT_TASK, "Task not found: '%s'" % task_id)


@app.route('/api/v1/tasks', methods=['GET'])
def get_tasks():
    debugRequest(flask.request)
    resp = flask.make_response(json.dumps(tasks), 200)
    return resp


@app.route('/api/v1/volumes/<volume_name>/objectKeyValues', methods=['POST'])
def create_key_value_pair(volume_name):
    debugRequest(flask.request)
    kv_pair = json.loads(flask.request.data.decode('utf-8'))
    key = kv_pair['key']
    value = kv_pair['value']

    if key is None:
        throw_error(400, INV_INPUT_MISSING_REQUIRED, 'key not specified.')

    if value is None:
        throw_error(400, INV_INPUT_MISSING_REQUIRED, 'value not specified.')

    if len(key) > 31 or len(value) > 31:
        throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                    'invalid input: string length exceeds limit')

    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in key or char in value:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Error parsing key or value')

    vol_exists = False
    for member in volumes['members']:
        if member['name'] == volume_name:
            vol_exists = True

            if 'metadata' not in member:
                member['metadata'] = {
                    'total': 0,
                    'members': []
                }

            for kv_pair in member['metadata']['members']:
                if kv_pair['key'] == key:
                    throw_error(409, EXISTENT_OBJECT_KEY,
                                "Key '%s' already exist." % key)

            member['metadata']['members'].append({'key': key, 'value': value})
            member['metadata']['total'] += 1
            break

    if not vol_exists:
        throw_error(404, NON_EXISTENT_VOL, "volume doesn't exist")

    return flask.make_response("Created", 201)


@app.route('/api/v1/volumes/<volume_name>/objectKeyValues/<key>',
           methods=['PUT'])
def update_key_value_pair(volume_name, key):
    debugRequest(flask.request)
    body = json.loads(flask.request.data.decode('utf-8'))
    value = body['value']

    if key is None:
        throw_error(400, INV_INPUT_MISSING_REQUIRED, 'key not specified.')

    if value is None:
        throw_error(400, INV_INPUT_MISSING_REQUIRED, 'value not specified.')

    if len(key) > 31 or len(value) > 31:
        throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                    'invalid input: string length exceeds limit')

    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in key or char in value:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Error parsing key or value')

    vol_exists = False
    for member in volumes['members']:
        if member['name'] == volume_name:
            vol_exists = True

            if 'metadata' not in member:
                throw_error(404, NON_EXISTENT_OBJECT_KEY,
                            "Key '%s' does not exist." % key)

            keyFound = False
            for kv_pair in member['metadata']['members']:
                if kv_pair['key'] == key:
                    kv_pair['value'] = value
                    keyFound = True

            if not keyFound:
                throw_error(404, NON_EXISTENT_OBJECT_KEY,
                            "Key '%s' does not exist." % key)

            break

    if not vol_exists:
        throw_error(404, NON_EXISTENT_VOL, "volume doesn't exist")

    return flask.make_response("OK", 200)


@app.route('/api/v1/volumes/<volume_name>/objectKeyValues/<key>',
           methods=['GET'])
def get_key_value_pair(volume_name, key):
    debugRequest(flask.request)

    if len(key) > 31:
        throw_error(400, INV_INPUT_EXCEEDS_LENGTH,
                    'invalid input: string length exceeds limit')

    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in key:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Error parsing key or value')

    vol_exists = False
    resp = None
    for member in volumes['members']:
        if member['name'] == volume_name:
            vol_exists = True

            if 'metadata' not in member:
                throw_error(404, NON_EXISTENT_OBJECT_KEY,
                            "Key '%s' does not exist." % key)

            keyFound = False
            for kv_pair in member['metadata']['members']:
                if kv_pair['key'] == key:
                    resp = flask.make_response(json.dumps(kv_pair), 200)
                    keyFound = True
                    break

            if not keyFound:
                throw_error(404, NON_EXISTENT_OBJECT_KEY,
                            "Key '%s' does not exist." % key)

            break

    if not vol_exists:
        throw_error(404, NON_EXISTENT_VOL, "volume doesn't exist")

    return resp


@app.route('/api/v1/volumes/<volume_name>/objectKeyValues', methods=['GET'])
def get_all_key_value_pairs(volume_name):
    debugRequest(flask.request)

    vol_exists = False
    resp = None
    for member in volumes['members']:
        if member['name'] == volume_name:
            vol_exists = True

            if 'metadata' not in member:
                member['metadata'] = {'total': 0, 'members': []}

            resp = flask.make_response(json.dumps(member['metadata']), 200)
            break

    if not vol_exists:
        throw_error(404, NON_EXISTENT_VOL, "volume doesn't exist")

    return resp


@app.route('/api/v1/volumes/<volume_name>/objectKeyValues/<key>',
           methods=['DELETE'])
def remove_key_value_pair(volume_name, key):
    debugRequest(flask.request)

    if key is None:
        throw_error(404, NON_EXISTENT_OBJECT_KEY,
                    "Key '%s' does not exist." % key)

    if len(key) > 31:
        throw_error(404, NON_EXISTENT_OBJECT_KEY,
                    "Key '%s' does not exist." % key)

    charset = {'!', '@', '#', '$', '%', '&', '^'}
    for char in charset:
        if char in key:
            throw_error(400, INV_INPUT_ILLEGAL_CHAR,
                        'Error parsing key or value')

    vol_exists = False
    for member in volumes['members']:
        if member['name'] == volume_name:
            vol_exists = True

            if 'metadata' not in member:
                throw_error(404, NON_EXISTENT_OBJECT_KEY,
                            "Key '%s' does not exist." % key)

            keyFound = False
            for i, kv_pair in enumerate(member['metadata']['members']):
                if kv_pair['key'] == key:
                    member['metadata']['members'].pop(i)
                    keyFound = True

            if not keyFound:
                throw_error(404, NON_EXISTENT_OBJECT_KEY,
                            "Key '%s' does not exist." % key)

            break

    if not vol_exists:
        throw_error(404, NON_EXISTENT_VOL, "volume doesn't exist")

    return flask.make_response("OK", 200)


if __name__ == "__main__":

    # fake 2 CPGs
    global cpgs
    cpgs = {'members':
            [{'SAGrowth': {'LDLayout': {'diskPatterns': [{'diskType': 1}]},
                           'incrementMiB': 8192},
              'SAUsage': {'rawTotalMiB': 24576,
                          'rawUsedMiB': 768,
                          'totalMiB': 8192,
                          'usedMiB': 256},
             'SDGrowth': {'LDLayout': {'diskPatterns': [{'diskType': 1}]},
                          'incrementMiB': 16384,
                          'limitMiB': 256000,
                          'warningMiB': 204800},
              'SDUsage': {'rawTotalMiB': 32768,
                          'rawUsedMiB': 2048,
                          'totalMiB': 16384,
                          'usedMiB': 1024},
              'UsrUsage': {'rawTotalMiB': 239616,
                           'rawUsedMiB': 229376,
                           'totalMiB': 119808,
                           'usedMiB': 114688},
              'additionalStates': [],
              'degradedStates': [],
              'domain': 'UNIT_TEST',
              'failedStates': [],
              'id': 0,
              'name': 'UnitTestCPG',
              'numFPVVs': 12,
              'numTPVVs': 0,
              'state': 1,
              'uuid': 'f9b018cc-7cb6-4358-a0bf-93243f853d96'},
             {'SAGrowth': {'LDLayout': {'diskPatterns': [{'diskType': 1}]},
                           'incrementMiB': 8192},
              'SAUsage': {'rawTotalMiB': 24576,
                          'rawUsedMiB': 768,
                          'totalMiB': 8192,
                          'usedMiB': 256},
              'SDGrowth': {'LDLayout': {'diskPatterns': [{'diskType': 1}]},
                           'incrementMiB': 16384,
                           'limitMiB': 256000,
                           'warningMiB': 204800},
              'SDUsage': {'rawTotalMiB': 32768,
                          'rawUsedMiB': 2048,
                          'totalMiB': 16384,
                          'usedMiB': 1024},
              'UsrUsage': {'rawTotalMiB': 239616,
                           'rawUsedMiB': 229376,
                           'totalMiB': 119808,
                           'usedMiB': 114688},
              'additionalStates': [],
              'degradedStates': [],
              'domain': 'UNIT_TEST',
              'failedStates': [],
              'id': 0,
              'name': 'UnitTestCPG2',
              'numFPVVs': 12,
              'numTPVVs': 0,
              'state': 1,
              'uuid': 'f9b018cc-7cb6-4358-a0bf-93243f853d97'}],
            'total': 2}

    # fake  volumes
    global volumes
    volumes = {'members':
               [{'additionalStates': [],
                 'adminSpace': {'freeMiB': 0,
                                'rawReservedMiB': 384,
                                'reservedMiB': 128,
                                'usedMiB': 128},
                 'baseId': 1,
                 'copyType': 1,
                 'creationTime8601': '2012-09-24T15:12:13-07:00',
                 'creationTimeSec': 1348524733,
                 'degradedStates': [],
                 'domain': 'UNIT_TEST',
                 'failedStates': [],
                 'id': 91,
                 'name': 'UnitTestVolume',
                 'policies': {'caching': True,
                              'oneHost': False,
                              'staleSS': True,
                              'system': False,
                              'zeroDetect': False},
                 'provisioningType': 1,
                 'readOnly': False,
                 'sizeMiB': 102400,
                 'snapCPG': 'UnitTestCPG',
                 'snapshotSpace': {'freeMiB': 0,
                                   'rawReservedMiB': 1024,
                                   'reservedMiB': 512,
                                   'usedMiB': 512},
                 'ssSpcAllocLimitPct': 0,
                 'ssSpcAllocWarningPct': 95,
                 'state': 1,
                 'userCPG': 'UnitTestCPG',
                 'userSpace': {'freeMiB': 0,
                               'rawReservedMiB': 204800,
                               'reservedMiB': 102400,
                               'usedMiB': 102400},
                 'usrSpcAllocLimitPct': 0,
                 'usrSpcAllocWarningPct': 0,
                 'uuid': '8bc9394e-f87a-4c1a-8777-11cba75af94c',
                 'wwn': '50002AC00001383D'},
                {'additionalStates': [],
                 'adminSpace': {'freeMiB': 0,
                                'rawReservedMiB': 384,
                                'reservedMiB': 128,
                                'usedMiB': 128},
                 'baseId': 41,
                 'comment': 'test volume',
                 'copyType': 1,
                 'creationTime8601': '2012-09-27T14:11:56-07:00',
                 'creationTimeSec': 1348780316,
                 'degradedStates': [],
                 'domain': 'UNIT_TEST',
                 'failedStates': [],
                 'id': 92,
                 'name': 'UnitTestVolume2',
                 'policies': {'caching': True,
                              'oneHost': False,
                              'staleSS': True,
                              'system': False,
                              'zeroDetect': False},
                 'provisioningType': 1,
                 'readOnly': False,
                 'sizeMiB': 10240,
                 'snapCPG': 'UnitTestCPG',
                 'snapshotSpace': {'freeMiB': 0,
                                   'rawReservedMiB': 1024,
                                   'reservedMiB': 512,
                                   'usedMiB': 512},
                 'ssSpcAllocLimitPct': 0,
                 'ssSpcAllocWarningPct': 0,
                 'state': 1,
                 'userCPG': 'UnitTestCPG',
                 'userSpace': {'freeMiB': 0,
                               'rawReservedMiB': 20480,
                               'reservedMiB': 10240,
                               'usedMiB': 10240},
                 'usrSpcAllocLimitPct': 0,
                 'usrSpcAllocWarningPct': 0,
                 'uuid': '6d5542b2-f06a-4788-879e-853ad0a3be42',
                 'wwn': '50002AC00029383D'}],
               'total': 26}

    # fake ports
    global ports
    ports = {'members':
             [{'linkState': 4,
               'mode': 2,
               'nodeWwn': None,
               'portPos': {'cardPort': 1, 'node': 1, 'slot': 7},
               'portWwn': '2C27D75375D5',
               'protocol': 2,
               'type': 7},
              {'linkState': 4,
               'mode': 2,
               'nodeWwn': None,
               'portPos': {'cardPort': 2, 'node': 2, 'slot': 8},
               'portWwn': '2C27D75375D6',
               'protocol': 2,
               'type': 7},
              {'linkState': 4,
               'mode': 2,
               'nodeWwn': None,
               'portPos': {'cardPort': 3, 'node': 3, 'slot': 5},
               'portWwn': '2C27D75375D7',
               'protocol': 1,
               'type': 7},
              {'linkState': 4,
               'mode': 2,
               'nodeWwn': None,
               'portPos': {'cardPort': 4, 'node': 4, 'slot': 6},
               'portWwn': '2C27D75375D8',
               'protocol': 1,
               'type': 7},
              {'portPos': {'node': 0, 'slot': 3, 'cardPort': 1},
               'protocol': 4,
               'linkState': 10,
               'label': 'RCIP0',
               'device': [],
               'mode': 4,
               'HWAddr': 'B4B52FA76931',
               'type': 7},
              {'portPos': {'node': 1, 'slot': 3, 'cardPort': 1},
               'protocol': 4,
               'linkState': 10,
               'label': 'RCIP1',
               'device': [],
               'mode': 4,
               'HWAddr': 'B4B52FA768B1',
               'type': 7}],
             'total': 6}

    # fake host sets
    global host_sets
    host_sets = {'members': [],
                 'total': 0}

    # fake hosts
    global hosts
    hosts = {'members':
             [{'FCWWNs': [],
               'descriptors': None,
               'domain': 'UNIT_TEST',
               'iSCSINames': [{'driverVersion': '1.0',
                               'firmwareVersion': '1.0',
                               'hostSpeed': 100,
                               'ipAddr': '10.10.221.59',
                               'model': 'TestModel',
                               'name': 'iqnTestName',
                               'portPos': {'cardPort': 1, 'node': 1,
                                           'slot': 8},
                               'vendor': 'HP'}],
               'id': 11,
               'name': 'UnitTestHost'},
              {'FCWWNs': [],
               'descriptors': None,
               'domain': 'UNIT_TEST',
               'iSCSINames': [{'driverVersion': '1.0',
                               'firmwareVersion': '1.0',
                               'hostSpeed': 100,
                               'ipAddr': '10.10.221.58',
                               'model': 'TestMode2',
                               'name': 'iqnTestName2',
                               'portPos': {'cardPort': 1, 'node': 1,
                                           'slot': 8},
                               'vendor': 'HP'}],
               'id': 12,
               'name': 'UnitTestHost2'}],
             'total': 2}

    # fake create vluns
    global vluns
    vluns = {'members':
             [{'active': True,
               'failedPathInterval': 0,
               'failedPathPol': 1,
               'hostname': 'UnitTestHost',
               'lun': 31,
               'multipathing': 1,
               'portPos': {'cardPort': 1, 'node': 1, 'slot': 2},
               'remoteName': '100010604B0174F1',
               'type': 4,
               'volumeName': 'UnitTestVolume',
               'volumeWWN': '50002AC00001383D'},
              {'active': False,
               'failedPathInterval': 0,
               'failedPathPol': 1,
               'hostname': 'UnitTestHost2',
               'lun': 32,
               'multipathing': 1,
               'portPos': {'cardPort': 2, 'node': 2, 'slot': 3},
               'type': 3,
               'volumeName': 'UnitTestVolume2',
               'volumeWWN': '50002AC00029383D'}],
             'total': 2}

    global volume_sets
    volume_sets = {'members': [],
                   'total': 0}

    global remote_copy_groups
    remote_copy_groups = {'members': [],
                          'total': 0}

    global target_remote_copy_groups
    target_remote_copy_groups = {'members': [],
                                 'total': 0}

    global qos_db
    qos_db = {'members': [],
              'total': 0}

    global tasks
    tasks = {"total": 2, "members":
             [{"id": 8933, "type": 15, "name": "check_slow_disk",
               "status": 1, "startTime": "2014-02-06 13:07:03 PST",
               "finishTime": "2014-02-06 14:03:04 PST", "priority": -1,
               "user": "3parsvc"},
              {"id": 8934, "type": 15, "name": "remove_expired_vvs",
               "status": 1, "startTime": "2014-02-06 13:27:03 PST",
               "finishTime": "2014-02-06 13:27:03 PST", "priority": -1,
               "user": "3parsvc"}]}
    app.run(port=args.port, debug=debugRequests)
