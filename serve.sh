#!/usr/bin/env bash
# Local preview of the GitHub Pages site with live reload.
# Usage: ./serve.sh   then open http://localhost:4000
set -e
cd "$(dirname "$0")"

docker run --rm -it \
  -v "$PWD":/site -w /site \
  -v gmrm-bundle:/usr/local/bundle \
  -e PAGES_REPO_NWO=anonymous/gmrm \
  -p 4000:4000 -p 35729:35729 \
  ruby:3.2 \
  bash -c "bundle install && bundle exec jekyll serve --host 0.0.0.0 --livereload --force_polling"
