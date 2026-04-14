#!/bin/bash
docker build -t habaldwin01/crab-ui:latest -t habaldwin01/crab-ui:$(git describe --tags) .
