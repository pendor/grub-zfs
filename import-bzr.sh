#!/bin/bash
#
# Script to update & import changes from Grub BZR into Git repo.
#
# Assumes that it's run within the git working directory.

set -e

BZR_DIR="../grub-bzr-gitmigrate"
BZR_MARKS=".git/bzr.marks"
GIT_MARKS=".git/git.marks"


if [ ! -d .git ] ; then
	echo "Please run me from inside your Git working dir."
	exit 1
fi

if [ ! -f "${BZR_MARKS}" ] ; then
	echo "No existing bzr history found."
	echo "We'll try a fresh import & hope for the best?"
fi

# Git isn't happy if this doesn't exist for some reason.
if [ ! -f "${GIT_MARKS}" ] ; then
	touch "${GIT_MARKS}"
fi

echo " "
echo "Updating BZR with upstream changes..."

pushd "${BZR_DIR}"

bzr pull && bzr update

popd

bzr fast-export --marks="${BZR_MARKS}" "${BZR_DIR}" | \
	git fast-import --import-marks="${GIT_MARKS}" --export-marks="${GIT_MARKS}"

echo " "
echo "Done.  You should be able to 'git push' any changes now."
echo " "
