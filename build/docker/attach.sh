#!/bin/bash
if [ -f /.dockerinit ] || [ -f /.dockerenv ]; then

    # activate python environment
    cd /workspace
    . /opt/bka_env/bin/activate

    # Help
    echo " | ip=`ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1  -d'/'`"
    echo " | start....: $ python server/webre-server.py -d"
    echo " | unittests: $ nosetests -vs tests/unit/"

    bash -i

else
    CONTAINER_ID=`docker ps | grep "w3dconverter:dev" | awk '{ print $1 }'`
    echo " * attaching to $CONTAINER_ID..."
    docker exec -it $CONTAINER_ID /bin/bash -i /tools/attach.sh $@
fi
