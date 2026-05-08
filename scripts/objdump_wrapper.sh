#!/bin/bash
input=$1
objdump -d "$input" > /dev/null 2>&1
