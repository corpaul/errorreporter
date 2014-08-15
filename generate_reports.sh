#!/bin/bash -xe

# run this puppy from a crontab :) paths are set for the VM running the errorreporter thingie
# TODO make paths configurable


cd /var/www/errorreporter/collected
rsync -rcnC --out-format="%f" all/ parsed/ --dry-run | xargs cp -t .

cd /var/www/errorreporter/errorreporter/djangoproject

. /var/www/errorreporter/env/bin/activate
python manage.py import_reports --input-dir=/var/www/errorreporter/collected/ --output-dir=/var/www/public_html/static/errorreporter/errorreporter/flamegraphs/
