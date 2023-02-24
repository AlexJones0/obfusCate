#!/bin/bash

# Determine which python executable path alias to use
if command -v python3 &> /dev/null
then  # Use python3 alias
  version_valid=`python3 -c 'import platform; ma, mi, _ = platform.python_version_tuple(); print(int(ma)>=3 and int(mi)$  pyexec=python3
else  # Use python alias
  version_valid=`python -c 'import platform; ma, mi, _ = platform.python_version_tuple(); print(int(ma)>=3 and int(mi)>$  pyexec=python
fi

# Check a valid python version is installed (> 3.8)
if [[ $version_valid == "True" ]]; then
  # Install required packages through PyPi
  $pyexec -m pip install -U -r requirements.txt
else
  echo "You are running an invalid python version. Please use version 3.8 or greater."
fi