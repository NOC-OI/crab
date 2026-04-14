#!/bin/bash
docker build -t habaldwin01/crab-worker:latest -t habaldwin01/crab-worker:$(git describe --tags) .
