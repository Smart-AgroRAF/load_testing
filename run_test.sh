#!/bin/bash

python main.py \
	--users 3 \
	--duration 10\
	--type paired \
	--mode api-blockchain \
	--run both \
	--contract both \
	--interval-requests 1 \
	--verbosity 10
