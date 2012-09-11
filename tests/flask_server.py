import pprint
from flask import Flask
from flask import request
import json

app = Flask(__name__)

@app.route('/hello')
def hello():
    return 'Hello World'

@app.route('/api/v1/credentials', methods=['GET', 'POST', 'DELETE'])
def credentials():
    pprint.pprint("REQUEST IS %s" % request.method)

    if request.method == 'POST':
        pprint.pprint("Request = %s" % request)
        pprint.pprint("data = %s" % request.data)
        pprint.pprint("Headers = %s" % request.headers)
        return 'POST credentials called'
    elif request.method == 'GET':
        pprint.pprint("data = %s" % request.data)
	data = json.loads(request.data.replace("\\\\",""))
	pprint.pprint(data['user'])
	pprint.pprint(data['password'])
        if data['user'] == 'user' and data['password'] == 'hp':
            #do something good here
            return 'GET AUTH PASS'
        else:
            #authentication failed!
            abort(401)
            return 'GET AUTH FAIL'
    elif request.method == 'DELETE':
        return 'DELETE credentials called'


if __name__ == "__main__":
    app.run()
