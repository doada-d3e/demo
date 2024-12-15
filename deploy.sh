#!/bin/bash

tag=$1

docker build . --tag demo_app:${tag}
docker tag demo_app:${tag} ${DOCKER_REGISTRY}/demo-app:latest
docker push ${DOCKER_REGISTRY}/demo-app:latest