#!/bin/bash

python main.py \
	--users 3 4 \
	--duration 10 10 \
	--type paired \
	--mode api-blockchain \
	--run static \
	--contract both \
	--interval-requests 1 \
	--repeat 3 \
	--warmup-duration 10
