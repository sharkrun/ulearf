#! /bin/bash

if [ "$1" = "" ];
then
    workroot=`pwd`
else
    workroot=$1
fi
export PYTHONPATH=".:$workroot"
PROCESS_NUM=`ps -ef | grep "python $workroot/main" | grep -v "grep" | wc -l`  
if [ $PROCESS_NUM -gt 0 ]; 
then
    ps -ef |grep "python $workroot/main" |awk '{print $2}' |while read pid
    do
        kill -9 $pid
    done    
else
    echo "the service is stoped!"
fi
if [ -f "$workroot/main.pyc" ]; then
    nohup python $workroot/main.pyc >$workroot/main.out &
else
    nohup python $workroot/main.py >$workroot/main.out &
fi
echo "--------------restarted---------------"

