#!/bin/bash

mkdir -p redis/tls
openssl genrsa -out redis/tls/ca.key 4096

openssl req \
     -x509 -new -nodes -sha256 \
     -key redis/tls/ca.key \
     -days 3650 \
     -subj '/O=Redis Test/CN=Certificate Authority' \
     -out redis/tls/ca.crt

openssl genrsa -out redis/tls/redis.key 2048
openssl req \
    -new -sha256 \
    -key redis/tls/redis.key \
    -subj '/O=Redis Test/CN=Server' | \
    openssl x509 \
        -req -sha256 \
        -CA redis/tls/ca.crt \
        -CAkey redis/tls/ca.key \
        -CAserial redis/tls/ca.txt \
        -CAcreateserial \
        -days 365 \
        -out redis/tls/redis.crt

openssl dhparam -out redis/tls/redis.dh 2048

chmod 644 redis/tls/*

echo "Redis TLS certificates generated in redis/tls. "
echo "Note: The permissions of the private key are set to 644 to \
allow the Docker container to read the key. \
Please evaluate the security implications of this setting in your environment."
