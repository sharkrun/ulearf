#!/bin/bash
echo "In build.sh"
set -e

cd $(dirname $0)/..

src_root=`pwd`

dir_name=${src_root##*/}

echo "src root:" ${src_root}
echo "dir name:" ${dir_name}

mkdir -p ${GOPATH}/src/ufleet

ln -s ${src_root} ${GOPATH}/src/ufleet/user

cd ${GOPATH}/src/ufleet/user
echo "change to" `pwd`

echo "CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -tags netgo -installsuffix cgo -o ufleet-user"
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -tags netgo -installsuffix cgo -o ufleet-user
echo "end of build.sh"