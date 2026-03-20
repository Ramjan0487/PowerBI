#!/usr/bin/env bash
set -euo pipefail
OUT="${1:-certs}"
mkdir -p "$OUT/ca" "$OUT/server" "$OUT/client"
echo "==> Generating Root CA..."
openssl genrsa -out "$OUT/ca/ca.key" 4096
openssl req -new -x509 -days 3650 -key "$OUT/ca/ca.key" -subj "/C=RW/O=ContractIQ/CN=ContractIQ-CA" -out "$OUT/ca/ca.crt"
echo "==> Generating server cert..."
openssl genrsa -out "$OUT/server/server.key" 2048
openssl req -new -key "$OUT/server/server.key" -subj "/C=RW/O=ContractIQ/CN=cms.company.com" -out "$OUT/server/server.csr"
openssl x509 -req -days 365 -in "$OUT/server/server.csr" -CA "$OUT/ca/ca.crt" -CAkey "$OUT/ca/ca.key" -CAcreateserial -out "$OUT/server/server.crt"
echo "==> Generating client cert..."
openssl genrsa -out "$OUT/client/client.key" 2048
openssl req -new -key "$OUT/client/client.key" -subj "/C=RW/O=ContractIQ/CN=cms-client" -out "$OUT/client/client.csr"
openssl x509 -req -days 365 -in "$OUT/client/client.csr" -CA "$OUT/ca/ca.crt" -CAkey "$OUT/ca/ca.key" -CAcreateserial -out "$OUT/client/client.crt"
openssl pkcs12 -export -in "$OUT/client/client.crt" -inkey "$OUT/client/client.key" -certfile "$OUT/ca/ca.crt" -out "$OUT/client/client.p12" -passout pass:cms2024
echo "Certs generated in $OUT/ (client.p12 password: cms2024)"
