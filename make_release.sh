#!/bin/bash
set -e

TWINE_REPOSITORY='mountbit'

CUR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${CUR_DIR}"

BIN_DIR="${CUR_DIR}/bin"
PYTHON="${CUR_DIR}/bin/python_twine"
TWINE="${CUR_DIR}/bin/twine"

cd src

echo "Build SDIST and WHEEL"
${PYTHON} -m build
echo
echo "Check dists by Twine"
${TWINE} check dist/*
rm -rf dist

echo
echo "Check not committed changes"
NOT_COMMITTED=$(git status --untracked-files=no --porcelain)
if [[ "$NOT_COMMITTED" ]]; then
  echo "ERROR: You have not committed changes!"
  exit 1
fi

echo
echo "Update version in CHANGES.rst"
VERSION='auto'
if [[ $1 ]]; then
  VERSION=$1
fi
VERSION=$(${PYTHON} version.py -u "${VERSION}")

if [[ -z "$VERSION" ]]
then
  echo "ERROR: File CHANGES.rst not changed!"
  exit 1
fi

NOT_COMMITTED=$(git status --untracked-files=no --porcelain)
if [[ "$NOT_COMMITTED" ]]
then
  echo "Commit updated CHANGES.rst for version ${VERSION}"
  git add CHANGES.rst
  git commit -m "Create release"
  echo Push changes to repository
  git push

  echo "Create tag v${VERSION}"
  git tag -a -f -m "Version ${VERSION}" "v${VERSION}"
  git push --tags
fi


echo "Make release"
${PYTHON} -m build
TWINE_REPOSITORY=${TWINE_REPOSITORY} ${TWINE} upload dist/*
rm -rf dist

cd "${CUR_DIR}"

echo OK
