#!/bin/bash

eval "$(ssh-agent -s)"
install --directory ~/.ssh --mode 700
base64 -d <<< "$SIGNING_KEY" > ~/.ssh/mex
base64 -d <<< "$SIGNING_PUB" > ~/.ssh/mex.pub
chmod 600 ~/.ssh/*
ssh-add ~/.ssh/mex
git config --local user.email "$MEX_BOT_EMAIL"
git config --local user.name "$MEX_BOT_USER"
git config --local gpg.format ssh
git config --local user.signingkey ~/.ssh/mex.pub
git config --local commit.gpgsign true
