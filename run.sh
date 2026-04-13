#!/bin/bash
docker run -d --name frepple-webserver-local --env-file .env -p 8000:8000 trivision-app:latest