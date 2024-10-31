#!/bin/bash
cd flask
bash build.sh
cd ..
docker compose up -d
