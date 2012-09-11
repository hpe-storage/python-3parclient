from flask import Flask, request, abort, redirect, url_for
import pprint
import json

app = Flask(__name__)

@app.route('/hello')
def hello():
    return 'Hello World'

@app.route('/api/v1/credentials', methods=['GET', 'POST', 'DELETE'])
def credentials():
    pprint.pprint("credentials %s" % request.method)

    if request.method == 'GET':
        pprint.pprint("Request = %s" % request)
        pprint.pprint("data = %s" % request.data)
        pprint.pprint("Headers = %s" % request.headers)
        return 'POST credentials called'

    elif request.method == 'POST':
        pprint.pprint("data = %s" % request.data)
	data = json.loads(request.data.replace("\\\\",""))

        if data['user'] == 'user' and data['password'] == 'hp':
            #do something good here
            pprint.pprint("authorized")
            return 'GET AUTH PASS'
        else:
            #authentication failed!
            pprint.pprint("auth failed")
            abort(401)

    elif request.method == 'DELETE':
        return 'DELETE credentials called'


if __name__ == "__main__":
    app.run()
