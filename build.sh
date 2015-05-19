#!/bin/bash

APP_NAME=slack_alerts

cd $(dirname $0)

mkdir -p dist tmp

echo "Cleaning staging environment..." >&2
rm -rf tmp/*

echo "Bootstrapping staging environment..." >&2
mkdir tmp/$APP_NAME
cp -r appserver bin default metadata README tmp/$APP_NAME/

echo "Building package..." >&2
VERSION=$(cat default/app.conf | grep -e 'version\s*=' | sed -e 's/version[ ]*=[ ]*//')
FILENAME=$APP_NAME-$VERSION-$(git rev-parse --short HEAD).spl

cd tmp
tar cvfz ../dist/$FILENAME $APP_NAME >&2

echo >&2
echo $FILENAME
