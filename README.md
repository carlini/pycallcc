# py-call/cc

<video src="https://user-images.githubusercontent.com/1269300/156979616-41b6dfd9-fd30-45f4-b5f6-f18bd0abba1f.mp4"></video>

## What problem does this solve?

Often I find myself in a situation where I am trying to quickly iterate on a function that can only be tested after some (slow to construct) state exists. Something like this:

```python
initialize_boring_state() # takes forever
do_something_interesting() # fast
```

This can be something as complicated as building a nasty in-memory datastructure that takes forever to construct, or as simple as loading a large amount of data off disk or just importing the TensorFlow library (which takes inordinately long). You can't actually go and do the interesting work until the slow thing has loaded. So what do you do?

Lots of people will tell you to go and just set up a jupyter notebook, put the first slow thing in the first cell, and then iterate on the second interesting function after having run the first cell once.

But what if you don't want to do that? This project gives another solution.

## What does this do?

You replace the above code with this.

```python
from pycallcc import wrap

@wrap
def initialize_boring_state():
    global my_complicated_datastructure
    my_complicated_datastructure = SomethingSlow()

if __name__ == "__main__":
    initialize_boring_state()
```

Now, after you've run this once, you can repeatedly interact with the datastructure in interesting ways, without having to ever re-compute the boring state. 

```python
from pycallcc import wrap

@wrap
def do_something_interesting(x):
    return my_complicated_datastructure.process(x)

if __name__ == "__main__":
    do_something_interesting(7)
```




## How does it work?


In the background we start a python script that runs and continuously holds on to the state of the world. Start this by running
```
python -m pycallcc.background
```

Then, you can wrap any function in the script you're interacting with. Whenever you call a function that has been wrapped with `@wrap` instead of running the code in the actual python process you're using, the code is run in the background process's environment instead. This means that the global state is preserved and so you can repeatedly try to iterate on a function that assumes a lot of global state without having to re-build it every time.

The way this actually happens is not so difficult. The background script runs a flask server, @wrap will replace function with a shim that will call to the background and return the response.


## What else does it do?

There are a couple of nice features.

1. The output from the background is streamed to the foreground instead of batched. This keeps the latency at almost exactly what it would be just running things directly.

2. If you kill the job, then the background thread that's doing the processing will also be killed automatically.

If this didn't happen then any time you killed the foreground job (because you realized you've made a mistake) then the background one would keep going and waste time doing nothing useful.


## What is it bad at doing?

It's better to not print a large amount of text. Every character that gets printed is sent in its own HTTP packet, so printing a few KB results in transmitting a few MB. (But it is safe to *return* large amounts of data.)


## Installing

To install just run this:

```
pip install -e .
```

## Why is it called pycallcc?

My initial design goal for this project was more ambitious. I wanted a call/cc like interface that would allow me to snapshot the python environment at arbitrary points in time (a la scheme's call/cc) and continue execution from those snapshots.

This is very much not that. But it does saves one global state around that you can keep working with, which if you squint hard enough might kind of look like an ugly call/cc. Maybe in the future I'll get inspired to go the full distance, but this is enough for now.


# API Reference

There are only a few commands that are used here.

## @wrap

This is the main decorator provided by this module. It wraps a function and any time it's called, the arguments get passed to the backend that runs it and then returns the result back to the script. Its use is described above.

## @only_once

This decorator wraps a function, and will only re-evaluate the function contents when the function itself changes. This lets you write a file that looks like

```python
from pycallcc import wrap, only_once

@only_once
@wrap
def setup():
    do_something_log("/path/to/data")

@wrap
def run():
    # use data

if __name__ == "__main__":
    setup()
    run()
```

Running this file multiple times will result in setup() being only called the first time it's executed, and run() being called every time. If the function setup() changes later on, for example by changing the data path to somewhere else, then setup() will be re-executed.


## @script

This command just wraps the entire remainder of the file in a big giant function and runs it in the main environment. It's useful only in a few random situations (like when something takes a long time to load the first time aronud, but not after that).

```python
from pycallcc import script
script()

print(5)
```

# License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.
