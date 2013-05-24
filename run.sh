#!/bin/bash

python setup.py build
cp build/lib.linux-armv6l-2.7/pidaqif.so .
echo "!!Ready"
read -p "!!Press [Enter] key to run test.py..." foo
python test.py
#python storage.py spi
