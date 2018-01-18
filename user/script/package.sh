#!/bin/bash
echo "package.sh"
set -e

cd $(dirname $0)/..

docker build -f Dockerfile -t user .
