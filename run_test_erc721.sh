#!/bin/bash

python main.py \
	--users 3 \
	--duration 10 \
	--type paired \
	--mode api-blockchain \
	--run static \
	--contract erc721 \
	--interval-requests 1
