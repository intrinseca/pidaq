#!/bin/sh

scp -rq * raspberrypi:deploy/pidaq
ssh raspberrypi "cd ~/deploy/pidaq && ./run.sh"
