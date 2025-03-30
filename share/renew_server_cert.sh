#!/bin/bash
#
# renew self-signed server cert
# thomas@linuxmuster.net
# 20250330
#

. /usr/share/linuxmuster/environment.sh || exit 1

DAYS="7305"
CACERT_OLD="${CACERT}_old"
CACERTB64_OLD="${CACERTB64}_old"
SRVCERT="$SSLDIR/server.cert.pem"
SRVCERT_OLD="${SRVCERT}_old"
SRVKEY="$SSLDIR/server.key.pem"
SRVBUNDLE="$SSLDIR/server.cert.bundle.pem"
SRVFULLCHAIN="$SSLDIR/server.fullchain.pem"
FWCERT="$SSLDIR/firewall.cert.pem"
FWCERT_OLD="${FWCERT}_old"
FWCERTB64="${FWCERT}.b64"
FWCERTB64_OLD="${FWCERTB64}_old"
FWKEY="$SSLDIR/firewall.key.pem"

# ca
echo "Renewing $(basename $CACERT) with $DAYS days."
mv "$CACERT" "$CACERT_OLD"
openssl x509 -days "$DAYS" -in "$CACERT_OLD" -signkey "$CAKEY" -passin pass:"$(cat "$CAKEYSECRET")" -out "$CACERT"
# export key for firewall without password
openssl rsa -in "$CAKEY" --passin pass:"$(cat "$CAKEYSECRET")" --out "${CAKEY}.extracted"
mv "$CACERTB64" "$CACERTB64_OLD"
base64 "$CACERT" | sed '{:q;N;s/\n//g;t q}' > "$CACERTB64"

# server
echo "Renewing $(basename $SRVCERT) with $DAYS days."
mv "$SRVCERT" "$SRVCERT_OLD"
openssl x509 -days "$DAYS" -in "$SRVCERT_OLD" -signkey "$SRVKEY" -out "$SRVCERT"
cat "$SRVCERT" "$SRVKEY" > "$SRVFULLCHAIN"
[ -e "$SRVBUNDLE" ] && mv "$SRVBUNDLE" "${SRVBUNDLE_old}"

# firewall
echo "Renewing $(basename $FWCERT) with $DAYS days."
mv "$FWCERT" "$FWCERT_OLD"
openssl x509 -days "$DAYS" -in "$FWCERT_OLD" -signkey "$FWKEY" -out "$FWCERT"
cat "$FWCERT" "$FWKEY" > "$FWFULLCHAIN"
mv "$FWCERTB64" "$FWCERTB64_OLD"
base64 "$FWCERT" | sed '{:q;N;s/\n//g;t q}' > "$FWCERTB64"

chgrp ssl-cert "$SSLDIR"/*
chmod 600 "$SSLDIR"/*key.*
