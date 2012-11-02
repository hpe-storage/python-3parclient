#from flask import Flask, request, abort, make_response, session, escape
from flask import *
import pprint
import json, os, random, string
import argparse
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException

parser = argparse.ArgumentParser()
parser.add_argument("-debug", help="Turn on http debugging", default=False, action="store_true")
args = parser.parse_args()
debugRequests = False
if "debug" in args and args.debug == True:
    debugRequests = True

#__all__ = ['make_json_app']

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
  return ''.join(random.choice(chars) for x in range(size))

def make_json_app(import_name, **kwargs):
    """
    Creates a JSON-oriented Flask app.

    All error responses that you don't specifically
    manage yourself will have application/json content
    type, and will contain JSON like this (just an example):

    { "message": "405: Method Not Allowed" }
    """
    def make_json_error(ex):
        pprint.pprint(ex)
        pprint.pprint(ex.code)
        #response = jsonify(message=str(ex))
        response = jsonify(ex)
        response.status_code = (ex.code
                                if isinstance(ex, HTTPException)
                                else 500)
        return response

    app = Flask(import_name, **kwargs)
    app.debug = True
    app.secret_key = id_generator(24)
    

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    return app

app = make_json_app(__name__)

session_key = id_generator(24)

def debugRequest(request):
    if debugRequests:
        print "\n"
        pprint.pprint(request)
        pprint.pprint(request.headers)
        pprint.pprint(request.data)


def throw_error(http_code, error_code=None, desc=None, debug1=None, debug2=None):
    if error_code:
        info = {'code': error_code, 'desc': desc}
        if debug1:
            info['debug1'] = debug1
        if debug2:
            info['debug2'] = debug2
        abort(Response(json.dumps(info), status=http_code))
    else:
        abort(http_code)

@app.route('/')
def index():
    debugRequest(request)
    if 'username' in session:
        return 'Logged in as %s' % escape(session['username'])
    abort(401)

@app.route('/api/v1/throwerror')
def errtest():
    debugRequest(request)
    throw_error(405, 'ERR_TEST', 'testing throwing an error', 'debug1 message', 'debug2 message')


@app.errorhandler(404)
def not_found(error):
    debugRequest(request)
    return Response("%s has not been implemented" % request.path, status=501)


@app.route('/api/v1/credentials', methods=['GET', 'POST'])
def credentials():
    debugRequest(request)

    if request.method == 'GET':
        return 'GET credentials called'

    elif request.method == 'POST':
	data = json.loads(request.data)

        if data['user'] == 'user' and data['password'] == 'hp':
            #do something good here
            try:
                resp = make_response(json.dumps({'key':session_key}), 201)
                resp.headers['Location'] = '/api/v1/credentials/%s' % session_key
                session['username'] = data['user']
                session['password'] = data['password']
                session['session_key'] = session_key
                return resp
            except Exception as ex:
                pprint.pprint(ex)

        else:
            #authentication failed!
            throw_error(401, "HTTP_AUTH_FAIL", "Username and or Password was incorrect")


@app.route('/api/v1/credentials/<session_key>', methods=['DELETE'])
def logout_credentials(session_key):
    debugRequest(request)
    session.clear()
    return 'DELETE credentials called'


#### CPG ####

@app.route('/api/v1/cpgs', methods=['POST'])
def create_cpgs():
    debugRequest(request)
    data = json.loads(request.data)

    valid_keys = {'name':None, 'growthIncrementMB':None, 'growthLimitMB':None, 
                  'usedLDWarningAlertMB':None, 'domain':None, 'LDLayout':None}

    valid_LDLayout_keys = {'RAIDType':None, 'setSize':None, 'HA':None, 
                           'chuckletPosRef':None, 'diskPatterns':None} 

    for key in data.keys():
        if key not in valid_keys.keys():
           throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % key)
        elif 'LDLayout' in data.keys():
           layout = data ['LDLayout']
           for subkey in layout.keys():
               if subkey not in valid_LDLayout_keys:
                   throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % subkey) 

    if data['domain'] == 'BAD_DOMAIN': 
	throw_error(404, 'NON_EXISTENT_DOMAIN', "Non-existing domain specified.")
    elif data['name'] == 'UniteTestCPG3': 
	throw_error(409, 'EXISTENT_CPG', "CPG '%s' already exist." % data['name'])
    
    #fake create 2 CPGs
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
 
    return  make_response("", 200)

@app.route('/api/v1/cpgs', methods=['GET'])
def get_cpgs():
    debugRequest(request)
    
    #should get it from global cpgs 
    resp = make_response(json.dumps(cpgs), 200)
    return resp

@app.route('/api/v1/cpgs/<cpg_name>', methods=['DELETE'])
def delete_cpg(cpg_name):
    debugRequest(request)

    if cpg_name == "NonExistCPG":
	throw_error(404, 'NON_EXISTENT_CPG', "CPG '%s' doesn't exist" % cpg_name)
    
    #fake delete
    cpgs = {'members':[], 'total':0} 
    return make_response("", 200)

#### Host ####

@app.route('/api/v1/hosts', methods=['POST'])
def create_hosts():
    debugRequest(request)
    data = json.loads(request.data)
    valid_keys = {'FCPaths':None, 'descriptors':None, 'domain':None, 'iSCSIPaths':None,
                  'id': 0,'name':None}

    valid_iscsi_keys = {'driverVersion': None, 'firmwareVersion':None, 'hostSpeed':None, 
                        'ipAddr': None, 'model':None, 'name': None, 'portPos': None,
                        'vendor': None}
 
    ## do some fake errors here depending on data
    for key in data.keys():
        if key not in valid_keys.keys():
           throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % key) 
        elif 'iSCSIPaths' in data.keys():
           iscsiP = data ['iSCSIPaths']
           for subkey in iscsiP.keys():
               if subkey not in valid_iscsi_keys:
                   throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % subkey) 

    #fake hosts
    global hosts 
    hosts = {'members': 
             [{'FCPaths': [],
               'descriptors': None,
               'domain': 'UNIT_TEST',
               'iSCSIPaths': [{'driverVersion': '1.0',
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
              {'FCPaths': [],
               'descriptors': None,
               'domain': 'UNIT_TEST',
               'iSCSIPaths': [{'driverVersion': '1.0',
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
    resp = make_response("", 201)
    return resp

@app.route('/api/v1/hosts/<host_name>', methods=['DELETE'])
def delete_host(host_name):
    debugRequest(request)

    if host_name == "UnitTestNonExistHost":
	throw_error(404, 'NON_EXISTENT_HOST', "The host '%s' doesn't exist" % host_name)
    elif host_name == "UnitTestInUseHost":
	throw_error(403, 'IN_USE', "The host '%s' is in-use" % host_name)

    #fake delete 
    hosts  = {'members':[], 'total':0} 
    return make_response("", 200)

@app.route('/api/v1/hosts', methods=['GET'])
def get_hosts():
    debugRequest(request)
    resp = make_response(json.dumps(hosts), 200)
    return resp

#### Port ####

@app.route('/api/v1/ports', methods=['GET'])
def get_ports():
    debugRequest(request)

    #fake ports 
    ports = {'members': 
             [{'linkState': 4,
               'mode': 2,
               'nodeWwn': None,
               'portPos': {'cardPort': 1, 'node': 1, 'slot': 8},
               'portWwn': '2C27D75375D6',
               'protocol': 2,
               'type': 7},
              {'linkState': 4,
               'mode': 2,
               'nodeWwn': None,
               'portPos': {'cardPort': 1, 'node': 1, 'slot': 8},
               'portWwn': '2C27D75375D6',
               'protocol': 2,
               'type': 7}],
            'total': 2}
    resp = make_response(json.dumps(ports), 200)
    return resp

#### VLUN ####

@app.route('/api/v1/vluns', methods=['POST'])
def create_vluns():
    debugRequest(request)
    data = json.loads(request.data)

    valid_keys = {'volumeName':None, 'lun':0, 'hostname':None, 'portPos':None,
                  'noVcn': False, 'overrideLowerPriority':False}
   
    
    valid_port_keys = {'node':1, 'slot':1, 'cardPort':0}
 
    ## do some fake errors here depending on data
    for key in data.keys():
        if key not in valid_keys.keys():
           throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % key) 
        elif 'portPos' in data.keys():
           portP = data ['portPos']
           for subkey in portP.keys():
               if subkey not in valid_port_keys:
                   throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % subkey) 

    if data['volumeName'] == 'UnitTestNonExistVolume':
        throw_error(404, 'NON_EXISTENT_VOL', "The vlun does not have volume '%s' exists" % data['volumeName'])
    elif data['hostname'] == 'UnitTestNonExistHost':
        throw_error(404, 'NON_EXISTENT_HOST', "The vlun does not have host '%s' exists" % data['hotname'])
    elif 'portPos' in data.keys() and data['portPos'] == '{\'node\':-1,\'slot\':-1,\'cardPort\':-1}':
        throw_error(404, 'NON_EXISTENT_PORT', "The vlun does not have port '%s' exists" % data['portPos'])
    elif data['volumeName'] == 'UnitTestLunTooLarge':
        throw_error(400, 'TOO_LARGE', "The VLUN size '%s' is too large" % data['lun'])
    elif data['lun'] == '10241024':
        throw_error(400, 'TOO_LARGE', "The VLUN '%s' is a existent lun" % data['volumeName'])

    #fake create vluns
    global vluns
  
    vluns = {'members': 
             [{'active': True,
               'failedPathInterval': 0,
               'failedPathPol': 1,
               'hostname': 'UnitTestHost',
               'lun': 1,
               'multipathing': 1,
               'portPos': {'cardPort': 1, 'node': 1, 'slot': 2},
               'remoteName': '100010604B0174F1',
               'type': 4,
               'volumeName': 'UnitTestVolume',
               'volumeWWN': '50002AC00001383D'}, 
              {'active': False,
               'failedPathInterval': 0,
               'failedPathPol': 1,
               'hostname': u'UnitTestHost2',
               'lun': 2,
               'multipathing': 1,
               'type': 3,
               'volumeName': u'UnitTestVolume2',
               'volumeWWN': u'50002AC00029383D'}],
            'total': 2}
 
    resp = make_response("", 201)
    if data['volumeName'] == 'UnitTestVolume':
       ret = 'UnitTestVolume,1,UnitTestHost,1:2:1' 
    elif data['volumeName'] == 'UnitTestVolume2':
       ret = 'UnitTestVolume,2,UnitTestHost' 
    
    resp.headers['location'] = '/api/v1/vluns/%s' % ret

    return resp 


@app.route('/api/v1/vluns/<vlun_str>', methods=['DELETE'])
def delete_vluns(vlun_str):
    #<vlun_str> is like volumeName,lun,host,node:slot:port
    debugRequest(request)

    if vlun_str == "NonExistVolume,1,UnitTestHost":
	throw_error(404, 'NON_EXISTENT_VLUN', "The volume '%s' doesn't exist" % vlun_str)
    elif vlun_str == "UnitTestVolume,1,NonExistHost":
	throw_error(404, 'NON_EXISTENT_HOST', "The host '%s' doesn't exist" % vlun_str)
    elif vlun_str == "UnitTestVolume,UnitTestHost,8:8:8":
	throw_error(404, 'NON_EXISTENT_PORT', "The lun '%s' doesn't exist" % vlun_str)

    #fake delete 
    vluns  = {'members':[], 'total':0} 
    return make_response("", 200)


@app.route('/api/v1/vluns', methods=['GET'])
def get_vluns():
    debugRequest(request)
    resp = make_response(json.dumps(vluns), 200)
    return resp


#### VOLUMES ####

@app.route('/api/v1/volumes/<volume_name>', methods=['POST'])
def create_snapshot(volume_name):
    debugRequest(request)
    data = json.loads(request.data)

    valid_keys = {'action': None, 'parameters': None}
    valid_parm_keys = {'name':None, 'id':None, 'comment': None,
                       'copyRO':None, 'expirationHours': None,
                       'retentionHours':None}

    ## do some fake errors here depending on data
    for key in data.keys():
        if key not in valid_keys.keys():
           throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % key)
        elif 'parameters' in data.keys():
           parm = data ['parameters']
           for subkey in parm.keys():
               if subkey not in valid_parm_keys:
                   throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % subkey) 

    if volume_name == "NonExistVolume":
	throw_error(404, 'NON_EXISTENT_VOLUME', "The volume '%s' doesn't exist" % volume_name)

    #return  make_response(request.data, 200)
    return  make_response("", 200)
 
@app.route('/api/v1/volumes', methods=['POST'])
def create_volumes():
    debugRequest(request)
    data = json.loads(request.data)

    valid_keys = {'name':None, 'cpg':None, 'sizeMiB':None, 'id':None,
                  'comment':None, 'policies':None, 'snapCPG':None,
                  'ssSpcAllocWarningPct': None, 'ssSpcAllocLimitPct': None,
                  'tpvv':None, 'usrSpcAllocWarningPct':None,
                  'usrSpcAllocLimitPct': None, 'isCopy':None,
                  'copyOfName':None, 'copyRO':None, 'expirationHours': None,
                  'retentionHours':None}

    ## do some fake errors here depending on data
    for key in data.keys():
        if key not in valid_keys.keys():
           throw_error(400, 'INV_INPUT', "Invalid Parameter '%s'" % key) 


    if data['name'] == 'UnitTestVolumeExists':
	throw_error(409, 'EXISTENT_SV', "The volume '%s' already exists" % data['name'])
    elif data['sizeMiB'] == 10241024:
	throw_error(400, 'TOO_LARGE', "Volume size '%s' above architectural limit" % data['sizeMiB'])
    elif data['sizeMiB'] == 9999:
	throw_error(400, 'NO_SPACE', "Not enough space currently available")
    
    #fake create volumes
    global volumes
  
    volumes = {'members': 
               [{'additionalStates': [],
                 'adminSpace': {'freeMiB': 0,
                                'rawReservedMiB': 384,
                                'reservedMiB': 128,
                                'usedMiB': 128},
                 'baseId': 1,
                 'copyType': 1,
                 'creationTime8601': u'2012-09-24T15:12:13-07:00',
                 'creationTimeSec': 1348524733,
                 'degradedStates': [],
                 'domain': 'UNIT_TEST',
                 'failedStates': [],
                 'id': 1,
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
                 'id': 2,
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
    #return  make_response(request.data, 200)
    return  make_response("", 200)


@app.route('/api/v1/volumes/<volume_name>', methods=['DELETE'])
def delete_volumes(volume_name):
    debugRequest(request)

    if volume_name == "NonExistVolume":
	throw_error(404, 'NON_EXISTENT_SV', "The volume '%s' doesn't exist" % volume_name)
    elif volume_name == "forbidden":
	throw_error(403, "PERM_DENIED", "Insufficient privileges to delete '%s'" % volume_name)
    elif volume_name == "retained":
	throw_error(403, "RETAINED", "Volume Retention for '%s' has not timed out" % volume_name)
    elif volume_name == "readonlychild":
	throw_error(403, "HAS_RO_CHILD", "Volume '%s' has a read only child" % volume_name)

    #fake delete 
    volumes  = {'members':[], 'total':0} 
    return make_response("", 200)


@app.route('/api/v1/volumes', methods=['GET'])
def get_volumes():
    debugRequest(request)
    resp = make_response(json.dumps(volumes), 200)
    return resp


if __name__ == "__main__":
    app.run()
