#!/bin/sh

protoc --python_out=protobuf samples.proto
protoc --python_out=protobuf network.proto
