#!/bin/sh

pid=$(ps |grep "ufleet-user" | grep -v "grep" | awk '{print $1}')
kill -10 ${pid}