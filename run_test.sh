#!/bin/bash

python main.py \
	--users 1 2 \
	--duration 5 5 \
	--type paired \
	--mode api-blockchain \
	--run static \
	--contract both \
	--interval-requests 1 \
	--repeat 2 \
	--warmup-users 2 \
	--warmup-duration 5
