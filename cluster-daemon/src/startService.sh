#! /bin/bash

if [ "$1" = "" ];
then
    workroot=`pwd`
else
    workroot=$1
    cd $workroot
fi

if [ ! -d "$workroot/trace/logs" ]; then
  mkdir -p $workroot/trace/logs
fi

export PYTHONPATH="."
PROCESS_NUM=`ps -ef | grep "python $workroot/main" | grep -v "grep" | wc -l`
if [ $PROCESS_NUM -gt 0 ];
then
    echo "the Service is already running!"
    exit 1
else
    if [ -f "$workroot/main.pyc" ]; then
        nohup python $workroot/main.pyc >$workroot/trace/logs/main.out 2>&1 &
    else
        nohup python $workroot/main.py >$workroot/trace/logs/main.out 2>&1 &
    fi
    echo "--------------exited---------------"

fi
