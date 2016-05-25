#!/bin/bash
set -e

CWD=$(cd $(dirname $0); pwd)
cp -a $CWD/../../src/requirements.txt "$CWD/requirements.txt"

(cd $CWD && {
    docker build --rm=true -t w3dconverter:dev .
})

rm "$CWD/requirements.txt"
