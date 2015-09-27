# pyRESTvk/setup.py
# Dan Allongo (daniel.s.allongo@gmail.com)

# Uses py2exe for compiling server.py
# python setup.py py2exe

from distutils.core import setup
import py2exe

setup(console=['server.py'])
