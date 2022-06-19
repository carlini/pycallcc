from distutils.core import setup

setup(
    name='pycallcc',
    version='0.1.0',
    description='A python library to cache intermediate computations.',
    url='https://github.com/carlini/pycallcc',
    author='Nicholas Carlini',
    author_email='nicholas@carlini.com',
    license='GPL',
    packages=['pycallcc'],
    install_requires=['requests', 'flask']
)

