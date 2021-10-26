import os
import zipfile
import flask
import json
from flask.json import jsonify
from io import BytesIO

with zipfile.ZipFile('./app/static/test.zip', mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
    with open('./app/test.py', 'rb') as bf:
        zf.write(bf.read(), arcname='hello.py')