from flask import Flask
app = Flask(__name__)

@app.route('/hello')
def hello():
    return 'Hello World'

@app.route('/api/v1/credentials')
def credentials():
    return 'credentials called'

if __name__ == "__main__":
    app.run()
