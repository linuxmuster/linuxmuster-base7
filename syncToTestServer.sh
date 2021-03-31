#!/bin/bash

VM_IP=10.9.0.1

sync() {
    rsync -avzp --chown 0:0 ./sbin/* root@$VM_IP:/usr/sbin/
    rsync -avzp --chown 0:0 ./lib/* root@$VM_IP:/usr/lib/linuxmuster/
}

sync

inotifywait -r -m -e close_write --format '%w%f' ./sbin ./lib | while read MODFILE
do
    echo need to rsync ${MODFILE%/*} ...
    sync
done