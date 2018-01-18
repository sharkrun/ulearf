#! /bin/sh

if [ -d ./src-pyc ];then
    rm -rf ./src-pyc/*
fi

mkdir src-pyc

cp -rf src/* src-pyc

# python -m compileall src-pyc

# rm -f $(find ./src-pyc -name "*.py" -print)
