#!/bin/bash
# build.sh
# Builds the Docker image from the local Dockerfile
# This script represents the build step that can be used in GitHub Actions (for ECR).

IMAGE_NAME="trivision-app"
IMAGE_TAG="latest"

echo "Building docker image: ${IMAGE_NAME}:${IMAGE_TAG}..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

if [ $? -eq 0 ]; then
    echo "=============================="
    echo "Build completed successfully."
    echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    echo "=============================="
else
    echo "Build failed!"
    exit 1
fi
