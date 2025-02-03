#!/bin/bash
bash build-all.sh
mkdir -p ./build
docker save -o ./build/crab-ui.tar crab/ui:latest
docker save -o ./build/crab-worker.tar crab/worker:latest
