#!/bin/bash
bash build-all.sh
mkdir -p ./build
docker save -o ./build/crab-ui-v$(git describe --tags).tar habaldwin01/crab-ui:$(git describe --tags)
docker save -o ./build/crab-worker-v$(git describe --tags).tar habaldwin01/crab-worker:$(git describe --tags)
