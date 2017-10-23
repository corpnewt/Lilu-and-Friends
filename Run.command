#!/bin/bash

py="$( which python )"
py3="$( which python3 )"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
python_install=""
script_name="Scripts/Updater.py"
arg="$1"

if [[ "$py3" == "" ]]; then
	# No python 3
	if [[ "$py" == "" ]]; then
		# No python 2 either
		echo "Python is not installed!"
		exit 1
	else
		python_install=$py
	fi
else
	python_install=$py3
fi

if [[ "$arg" != "" ]]; then
	# We got an arg passed - try to launch it
	"$python_install" "$arg"
else
	"$python_install" "$DIR"/"$script_name"
fi