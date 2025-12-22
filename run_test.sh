#!/bin/bash

python main.py \
	--users 3 5 10 \
	--duration 10 10 10\
	--type paired \
	--mode api-blockchain \
	--run static \
	--contract both \
	--interval-requests 1
