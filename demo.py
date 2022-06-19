import pycallcc
from pycallcc import wrap, only_once

@only_once
@wrap
def setup_fib():
    global fib_nums

    def fib(x):
        if x < 1: return 1
        return fib(x-1) + fib(x-2)

    fib_nums = []

    for i in range(33):
        n = fib(i)
        print(n)
        fib_nums.append(n)

    print(fib_nums)

@wrap
def process_fib():
    import random
    print("Here's a random number:", random.choice(fib_nums))


if __name__ == "__main__":
    setup_fib()
    process_fib()
