#! /bin/sh


cd src
pyinstaller --hidden-import 'pkg_resources' -F main.py
