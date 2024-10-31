#!/bin/bash
cd src
gunicorn -w 4 main:app -b 0.0.0.0
