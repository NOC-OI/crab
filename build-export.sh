#!/bin/bash
cd flask
bash build.sh
cd ..
mkdir -p ./build
docker save -o ./build/crab.tar crab/ui:latest
