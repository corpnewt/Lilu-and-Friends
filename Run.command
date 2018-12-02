#!/usr/bin/env bash

[[ -x "$( command -v python3 )" ]] && python3="true"
[[ -x "$( command -v python )" ]] && python="true"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
python_install=""
script_name="Scripts/updater.py"

if [[ ! "$python3" ]]; then
	if [[ ! "$python" ]]; then
		echo "Python not found! Please install Python2 or Python3."
		exit 1
	else
		python_install="python"
	fi
else
	python_install="python3"
fi

"$python_install" "$DIR"/"$script_name" "$@"
