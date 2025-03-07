## Copyright (C) 2016, Nicholas Carlini <nicholas@carlini.com>.
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

from flask import Flask
from flask import request
from flask import Response
from queue import Queue
import signal
import time
import importlib
import base64
import sys
import traceback
import pickle
import threading
import os

import threading
import inspect
import ctypes

app = Flask(__name__)

RUNNING_THREAD = None

class RedirectOutput(object):
    encoding = 'UTF-8'
    def __init__(self, stream, name):
        self.stream = stream
        self.name = name
        self.buffer = None
        self._wrapped = False
        self.rich_proxied_file = None
    def write(self, data):
        self.stream.put(pickle.dumps([self.name, data]))
    def writelines(self, datas):
        self.stream.put(pickle.dumps([self.name, datas]))
    def flush(self):
        pass
    def isatty(self):
        return False
    def __getattr__(self, attr):
        raise
        return getattr(self.stream, attr)

    
class KillableThread(threading.Thread):
    def kill(self):
        # To be honest I don't actaully understand why this works.
        # I'm not sure if it's even supposed to or just happens to...
        # So not "you are not supposed to understand this"
        # But also I guess "I am not supposed to understand this"?
        if not self.is_alive():
            return
        
        for tid, tobj in threading._active.items():
            if tobj is self:
                break
        else:
            raise Exception("There's no active thread.")
        tid = ctypes.c_long(tid)
        
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid,
                                                         ctypes.py_object(SystemExit))
        if res == 0:
            raise Exception("Invalid thread.")
        elif res == 1:
            pass # Everything's great
        else:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise Exception("Something went very wrong when killing a thread.")


def do_it__I_AM_BACKGROUND_DONT_RELOAD(path, name, which, args, result):
    path = base64.b64decode(path.replace("_","/")).decode('ascii')
    name = base64.b64decode(name.replace("_","/")).decode('ascii')
    which = base64.b64decode(which.replace("_","/")).decode('ascii')
    args, kwargs = pickle.loads(base64.b64decode(args.replace("_","/")))
    fout = RedirectOutput(result, 'stdout')
    ferr = RedirectOutput(result, 'stderr')
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = fout, ferr
    res = None
    try:
        if path not in sys.path:
            sys.path.append(path)
        os.chdir(path)
        if name not in sys.modules:
            module = __import__(name)
        else:
            module = __import__(name)
            importlib.reload(module)
        if which != '__DONOTHING__':
            # When we are running a script top-down, then we pass this donothing.
            res = getattr(module, which)(*args, **kwargs)
            result.put(pickle.dumps(["result", res]))
    except Exception as err:
        exc = traceback.format_exc()
        result.put(pickle.dumps(["traceback", exc]))
    finally:
        sys.stdout, sys.stderr = stdout, stderr

    
@app.route("/do/", methods=['POST'])
def do():
    global RUNNING_THREAD

    path = request.form['module_name']
    name = request.form['file_name']
    function = request.form['function_name']
    args = request.form['arguments']
    
    if RUNNING_THREAD is not None:
        print("ERROR!! Tried to start a job when a prior job is still running. Cowardly refusing.")
        return "NACK"

    result = Queue()
    RUNNING_THREAD = KillableThread(target=do_it__I_AM_BACKGROUND_DONT_RELOAD, args=[path, name, function, args, result])
    RUNNING_THREAD.start()

    def generate():
        global RUNNING_THREAD
        # race condition here
        while RUNNING_THREAD and RUNNING_THREAD.is_alive():
            while not result.empty():
                top = result.get()
                yield base64.b64encode(top)+b"\n"
            time.sleep(.1)
        # check once more for data... 'cause we waited I guess it's safe?
        while not result.empty():
            top = result.get()
            yield base64.b64encode(top)+b"\n"
        RUNNING_THREAD = None

    return Response(generate())

@app.route("/kill", methods=['GET'])
def kill():
    global RUNNING_THREAD
    if RUNNING_THREAD is not None:
        RUNNING_THREAD.kill()
        RUNNING_THREAD = None
    return "ok"

@app.route("/status", methods=['GET'])
def status():
    return "alive"


def handler(signum, frame):
    exit(1)
    
    
signal.signal(signal.SIGINT, handler)    

if __name__ == "__main__":
    app.run(threaded=True, port=19568)
