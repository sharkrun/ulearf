#!/bin/bash
set -e

cd $(dirname $0)/..

src_root=`pwd`

dir_name=${src_root##*/}

docker run --rm  \
    -v ${src_root}:/root/user \
    golang:1.7 /root/user/script/build.sh
