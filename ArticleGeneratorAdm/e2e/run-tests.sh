#!/bin/bash
set -e
cd /Users/linsywu/Documents/AI-space/ArticleGenerator/ArticleGeneratorAdm
node_modules/.bin/playwright test --grep "$1" 2>&1
