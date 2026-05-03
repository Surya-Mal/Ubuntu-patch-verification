#!/bin/bash
INPUT_FILE=$1
echo "aa" | grep -E -f "$INPUT_FILE"
