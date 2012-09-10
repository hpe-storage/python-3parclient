import pprint
from flask import Flask
from flask import request

app = Flask(__name__)

@app.route('/hello')
def hello():
    return 'Hello World'

@app.route('/api/v1/credentials', methods=['GET', 'POST'])
def credentials():
    if request.method == 'POST':
        pprint.pprint("Request = %s" % request)
        pprint.pprint("data = %s" % request.data)
        pprint.pprint("Headers = %s" % request.headers)
        return 'POST credentials called'
    else:
        return 'GET credentials called'


if __name__ == "__main__":
    app.run()
