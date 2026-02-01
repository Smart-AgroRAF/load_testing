#!/bin/bash

python main.py \
	--users 1 10 20 30 40 50 60 70 80 90 100 \
	--duration 100 100 100 100 100 100 100 100 100 100 100 \
	--type paired \
	--mode api-blockchain \
	--run static \
	--contract both \
	--interval-requests 1 \
	--repeat 5 \
	--warmup-users 10 \
	--warmup-duration 100 \
	--warmup-interval-requests 1
