#!/bin/bash
set -e

cd $(dirname $0)/..

docker build -f Dockerfile.build -t ufleet-user-build .