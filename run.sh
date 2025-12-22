#!/bin/bash

python main.py \
	--users 1 10 20 30 40 50 60 70 80 90 100 110 120 130 140 150 \
	--duration 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 \
	--type paired \
	--mode api-blockchain \
	--run static \
	--contract both \
	--interval-requests 1 \
	--warmup-duration 20
