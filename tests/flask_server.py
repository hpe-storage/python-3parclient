#from flask import Flask, request, abort, make_response, session, escape
from flask import *
import pprint
import json, os, random, string
import argparse
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException
from flask_debugtoolbar import DebugToolbarExtension

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
def credentials_logout(session_key):
    debugRequest(request)
    session.clear()
    return 'DELETE credentials called'


@app.route('/api/v1/volumes', methods=['GET'])
def volumes_get():
    debugRequest(request)

    volume1 = { 'id': 1, 'name': 'Volume1', 'domain': 'somedomain',
               'provisioning' : 1, 'copyType' : 2, 'baseld' : 12345,
               'readOnly' : False, 'state' : 1, 'failedStates' : None,
               'degradedStates' : None, 'additionalStates' : None,
               'adminReservedMB' : 222, 'rawAdminReservedMB' : 111,
               'adminUsedMB': 5432, 'adminFreeMB' : 1234567890,
               'snapshotReservedMB' : 123, 'rawSnapshotReservedMB' : 123,
               'snapshotUsedMB' : 111, 'snapshotFreeMB': 222,
               'rawUserReservedMB' : 999, 'userUsedMB': 123456,
               'userFreeMB': 987654321, 'sizeMB' : 9876543210,
               'parentld' : '123', 'roChildld' : '444',
               'rwChildld' : '555', 'physParentld' : '777', 'wmn':'someWMN',
               'creationTimeSec' : 123456789, 'creationTime8601' : 'uhhh',
               'expirationTimeSec' : 2222222, 'expirationTime8601' : 33333333,
               'retentionTimeSec' : 44444444, 'retentionTime8601' : 55555555,
               'policies' : {'staleSS' : False, 'oneHost' : True, 
                             'zeroDetect' : True, 'system' : False, 
                             'caching' : True}, 
               'userCPG' : "SomethingCPG",
               'snapCPG' : "SomeSnapCPG", 'comment' : "this is a bogus volume!"}

    volume2 = { 'id': 2, 'name': 'Volume2', 'domain': 'anotherdomain',
               'provisioning' : 1, 'copyType' : 2, 'baseld' : 12345,
               'readOnly' : False, 'state' : 1, 'failedStates' : None,
               'degradedStates' : None, 'additionalStates' : None,
               'adminReservedMB' : 222, 'rawAdminReservedMB' : 111,
               'adminUsedMB': 5432, 'adminFreeMB' : 1234567890,
               'snapshotReservedMB' : 123, 'rawSnapshotReservedMB' : 123,
               'snapshotUsedMB' : 111, 'snapshotFreeMB': 222,
               'rawUserReservedMB' : 999, 'userUsedMB': 123456,
               'userFreeMB': 987654321, 'sizeMB' : 9876543210,
               'parentld' : '123', 'roChildld' : '444',
               'rwChildld' : '555', 'physParentld' : '777', 'wmn':'someWMN',
               'creationTimeSec' : 123456789, 'creationTime8601' : 'uhhh',
               'expirationTimeSec' : 2222222, 'expirationTime8601' : 33333333,
               'retentionTimeSec' : 44444444, 'retentionTime8601' : 55555555,
               'policies' : {'staleSS' : False, 'oneHost' : True, 
                             'zeroDetect' : True, 'system' : False, 
                             'caching' : True}, 
               'userCPG' : "SomethingCPG",
               'snapCPG' : "SomeSnapCPG", 'comment' : "another bogus volume!"}

    resp = make_response(json.dumps([volume1, volume2]), 200)
    return resp

@app.route('/api/v1/volumes', methods=['POST'])
def volumes_post():
    throw_error(501, 'BLAH', "Not implemented yet dude!")
     

@app.route('/api/v1/volumes', methods=['DELETE'])
def volumes_delete():
    throw_error(501, 'BLAH', "Not implemented yet dude!")



if __name__ == "__main__":
    app.run()
