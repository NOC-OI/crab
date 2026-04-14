#!/bin/bash
docker push habaldwin01/crab-ui:$(git describe --tags)
docker push habaldwin01/crab-ui:latest
docker push habaldwin01/crab-worker:$(git describe --tags)
docker push habaldwin01/crab-worker:latest
