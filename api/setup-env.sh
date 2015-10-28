#!/bin/bash

ENVDIR=$PWD/../../ENV
ENVDIR=`python -c 'import sys, os; print os.path.abspath(sys.argv[1])' "$ENVDIR"`

export PYTHONPATH="$PWD/lib:$ENVDIR:$PYTHONPATH"
export PATH="$ENVDIR/bin:$PATH"

function project-install() {
    if [ ! -d $ENVDIR ]; then
	virtualenv $ENVDIR
    fi
    pip install -r requirements.txt
}

