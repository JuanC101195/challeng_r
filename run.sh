#!/bin/bash

if [ -z "$CRED_KEY" ]; then
  echo "CRED_KEY is not set or is empty"
else
  ccrypt -d --envvar CRED_KEY credentials.json.cpt \
    && python src/__init__.py "$@"
fi
