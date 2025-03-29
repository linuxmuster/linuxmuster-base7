#!/bin/bash
#
# renew self-signed server cert
# thomas@linuxmuster.net
# 20250329
#

. /usr/share/linuxmuster/defaults.sh || exit 1

DAYS="7300"

# ca
echo "Renewing $(basename $CACERT) with $DAYS days."
CACERT_OLD="${CACERT}_old"
mv "$CACERT" "$CACERT_OLD"
openssl x509 -days "$DAYS" -in "$CACERT_OLD" -signkey "$CAKEY" -passin pass:"$(cat "$CAKEYSECRET")" -out "$CACERT"
# export key for firewall without password
openssl rsa -in "$CAKEY" --passin pass:"$(cat "$CAKEYSECRET")" --out "${CAKEY}.extracted"
base64 "$CACERT" | sed '{:q;N;s/\n//g;t q}' > "$CACERTB64"

# server
SRVCERT="$SSLDIR/server.cert.pem"
echo "Renewing $(basename $SRVCERT) with $DAYS days."
SRVCERT_OLD="${SRVCERT}_old"
SRVKEY="$SSLDIR/server.key.pem"
SRVBUNDLE="$SSLDIR/server.cert.bundle.pem"
mv "$SRVCERT" "$SRVCERT_OLD"
openssl x509 -days "$DAYS" -in "$SRVCERT_OLD" -signkey "$SRVKEY" -out "$SRVCERT"
cat "$SRVCERT" "$SRVKEY" > "$SRVBUNDLE"

# firewall
if [ ! -e "${FWFULLCHAIN}_old" ]; then
  echo "Moving obsolete firewall cert files."
  for i in "$SSLDIR"/firewall.*; do
    mv "$i" "${i}_old"
  done
fi

chgrp ssl-cert "$SSLDIR"/*
chmod 600 "$SSLDIR"/*key.*
