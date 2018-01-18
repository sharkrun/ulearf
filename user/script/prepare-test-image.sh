#!/bin/bash
set -e

cd $(dirname $0)/..

docker build -f Dockerfile.test -t ufleet-user-test .