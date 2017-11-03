#!/bin/sh
set -e

NOT_COMMITED=`git status --untracked-files=no --porcelain`
if [ "$NOT_COMMITED" ]
then
    echo ERROR: You have not commited changes!
    exit 1
fi

cd src
VERSION='auto'
if [ $1 ]
then
    VERSION=$1
fi
VERSION=`python version.py -u ${VERSION}`

if [ -z "$VERSION" ]
then
    echo ERROR: File CHANGES.txt not changed!
    exit 1
fi

NOT_COMMITED=`git status --untracked-files=no --porcelain`
if [ "$NOT_COMMITED" ]
then
    echo Commit updated CHANGES.txt for version ${VERSION}
    git add CHANGES.txt
    git commit -m "Create release"
    echo Push changes to repository
    git push

    echo Create tag v${VERSION}
    git tag -a -f -m "Version ${VERSION}" v${VERSION}
    git push --tags
fi

echo Make release
rm -rf dist
../bin/python setup.py sdist bdist_wheel
../twine upload dist/*
rm -rf dist
rm -rf build

cd ..

echo OK
