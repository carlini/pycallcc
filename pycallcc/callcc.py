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

import signal
import requests
import base64
import inspect
import threading
import time
import sys
import pickle
import functools
import traceback
import os

PORT = 19568

# This is a complete hack.
# It works on my systems, but maybe not on yours?
# If that's the case let me know.
AM_I_BACKGROUND = False or sys.argv == ['-m']
if len(inspect.stack()) > 2:
    for q in inspect.stack():
        if q.function == 'do_it__I_AM_BACKGROUND_DONT_RELOAD':
            AM_I_BACKGROUND = True


def kill_background(*args, **kwargs):
    try:
        requests.get("http://localhost:%d/kill"%PORT)
    except:
        pass
        
if not AM_I_BACKGROUND:
    import atexit
    atexit.register(kill_background)

    signal.signal(signal.SIGTERM, kill_background)
    signal.signal(signal.SIGINT, kill_background)

def wrapped_fn(function_ref, module_name, file_name, function_name):
    @functools.wraps(function_ref)
    def fn(*args, **kwargs):
        arguments = base64.b64encode(pickle.dumps([args, kwargs])).decode("ascii").replace("/","_")
        with requests.post("http://localhost:%d/do/"%PORT,
                           data = {'module_name': module_name,
                                   'file_name': file_name,
                                   'function_name': function_name,
                                   'arguments': arguments},
                          stream=True) as resp:
            to_raise = None
            building = []
            for x in resp.iter_content(1):
                if x != b"\n":
                    building.append(x)
                    continue
                name, out = pickle.loads(base64.b64decode(b"".join(building)))
                if name == "stdout":
                    sys.stdout.write(out)
                elif name == "stderr":
                    sys.stderr.write(out)
                elif name == "result":
                    return out
                elif name == "traceback":
                    # Make the exception pretty
                    # First, we print out the Traceback line
                    sys.stderr.write(out.split("\n")[0]+"\n")
                    # Then, print how we got to the method that entered the background
                    sys.stderr.write("".join(traceback.format_stack(limit=-1))[:-1]+"\n")
                    # After that we print out the real traceback from the background
                    # We have to muck with it a bit to hide the stack frame that
                    # kicked things off in the background, so skip 3 lines
                    sys.stderr.write("\n".join(out.split("\n")[3:])[:-1]+"\n")
                    exit(1)
                    
                        
                building = []
                    
        return None
    return fn

if not AM_I_BACKGROUND:
    def only_once(x): return x

    no_connection = True
    try:
        if requests.get("http://localhost:%d/status"%PORT).content == b'alive':
            no_connection = False
    except:
        pass
    
    if no_connection:
        print("Failed to establish connection; running locally")
        def script(): pass
        def wrap(x): return x
    else:
        def wrap(function_ref=None):
            if function_ref is None:
                return AM_I_BACKGROUND
            if AM_I_BACKGROUND: return function_ref
            module_name = dict(inspect.getmembers(function_ref))['__globals__']['__file__'][:-3]
            _, _, file_name = module_name.rpartition("/")
            module_name = os.getcwd()
            module_name = base64.b64encode(module_name.encode("ascii")).decode("ascii").replace("/","_")
            file_name = base64.b64encode(file_name.encode("ascii")).decode("ascii").replace("/","_")
            function_name = function_ref.__name__
        
            function_name = base64.b64encode(function_name.encode("ascii")).decode("ascii").replace("/","_")
        
            return wrapped_fn(function_ref, module_name, file_name, function_name)
        
        def script():
            if not AM_I_BACKGROUND:
                module_name = inspect.stack()[1].filename[:-3]
                _, _, file_name = module_name.rpartition("/")
                module_name = os.getcwd()
                file_name = base64.b64encode(file_name.encode("ascii")).decode("ascii").replace("/","_")
                
                module_name = base64.b64encode(module_name.encode("ascii")).decode("ascii").replace("/","_")
                function_name = '__DONOTHING__'
                function_name = base64.b64encode(function_name.encode("ascii")).decode("ascii").replace("/","_")
        
                def foo():
                    pass
                fn = wrapped_fn(foo, module_name, file_name, function_name)
                fn()
                exit(0)

elif AM_I_BACKGROUND:
    def script(): pass
    def wrap(x): return x
    last_code = {}
    def only_once(function_ref):
        @functools.wraps(function_ref)
        def fn(*args, **kwargs):
            arguments = pickle.dumps([args, kwargs])
            fn_args = dict(inspect.getmembers(function_ref))
            new_code = inspect.getsource(function_ref)
            k = (fn_args['__module__'], fn_args['__name__'])
            if (new_code, arguments) == last_code.get(k):
                return
            else:
                out = function_ref(*args, **kwargs)
                # Only counts if it didn't crash
                last_code[k] = (new_code, arguments)
                return out
    
        return fn
