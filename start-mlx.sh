#!/bin/bash
# Serves Qwen3.5 4B with thinking OFF by default (otherwise hidden reasoning eats the token budget).
source /Volumes/Acer/JARVIS/env.sh
cd /Volumes/Acer/JARVIS/OpenJarvis
exec uv run python -m mlx_lm server --model mlx-community/Qwen3.5-4B-MLX-4bit --port 8080 \
  --chat-template-args '{"enable_thinking": false}'
