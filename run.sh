#!/usr/bin/env bash

USE_GUI=$1

shift
source venv/bin/activate
python Smartlock2.py $USE_GUI