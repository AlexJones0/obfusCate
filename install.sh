#!/bin/bash

# Determine which python executable path alias to use
if command -v python3 &> /dev/null; 
then  # Use python3 alias
  pyexec="python3"
elif command -v python &> /dev/null;
then  # Use python alias
  pyexec="python"
elif command -v py &> /dev/null;
then
  pyexec="py"
else
  echo "A valid python path could not be found, so the script could not successfully complete."
  exit 1
fi

version_valid=`($pyexec -c 'import platform; ma, mi, _ = platform.python_version_tuple(); print(int(ma)>=3 and int(mi)>=10)')`  

# Check a valid python version is installed (>= 3.10)
if [[ $version_valid == "True" ]]; then
  # Install required packages through PyPi
  $pyexec -m pip install -U -r requirements.txt
else
  echo "You are running an invalid python version. Please use version 3.10 or greater."
  exit 1
fi
