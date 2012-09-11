#from flask import Flask, request, abort, make_response, session, escape
from flask import *
import pprint
import json
import os

import pkg_resources
pprint.pprint(pkg_resources.get_distribution('flask').version)

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

session_key = "abc123"

def make_good_response(body):
    resp = make_response(body, 200)
    resp.headers['X-InFormAPI-SessionKey'] = session_key
    return resp

def set_session_data(session, data, response):
    session['username'] = data['user']
    session['password'] = data['password']
    session['X-InFormAPI-SessionKey'] = response.headers['X-InFormAPI-SessionKey']
    
   
@app.route('/')
def index():
    if 'username' in session:
        return 'Logged in as %s' % escape(session['username'])
    abort(401)

@app.route('/hello')
def hello():
    return 'Hello World'

@app.route('/api/v1/credentials', methods=['GET', 'POST'])
def credentials():
    pprint.pprint("credentials %s" % request.method)
    #pprint.pprint("data = %s" % request.data)

    if request.method == 'GET':
        return 'GET credentials called'

    elif request.method == 'POST':
	data = json.loads(request.data)

        if data['user'] == 'user' and data['password'] == 'hp':
            #do something good here
            pprint.pprint("authorized")
            try:
                resp = make_good_response("Auth Worked")
                set_session_data(session, data, resp)
                #pprint.pprint(resp.headers)
                return resp
            except Exception as ex:
                pprint.pprint(ex)

        else:
            #authentication failed!
            pprint.pprint("auth failed")
            abort(401)


@app.route('/api/v1/credentials/<session_key>', methods=['DELETE'])
def credentials_logout(session_key):
    pprint.pprint("credentials %s" % request.method)
    session.clear()
    return 'DELETE credentials called'



if __name__ == "__main__":
    app.run(debug=True)
