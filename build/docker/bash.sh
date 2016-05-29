#!/bin/bash
if [ -f /.dockerinit ] || [ -f /.dockerenv ]; then
    # bash history
    touch /tools/.bash_history
    ln -s -F /tools/.bash_history ~/.bash_history

    # activate python environment
    cd /workspace
    . /opt/py3_env/bin/activate

    # Help
    echo " | ip=`ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1 -d'/'`"
    echo " | start....: $ python server/bka-server.py -d"
    echo " | unittests: $ nosetests -vs tests/unit/"

    # colored prompt
    echo 'PS1="(py3_env) \[\033[38;5;6m\]\w\[\033[38;5;15m\]\\$ "' >> /root/.bashrc

    # Execute bash or cmd
    bash -i # -c $@

else
    CWD=$(cd $(dirname $0); pwd)
    WORKSPACE=$(cd "$CWD/../.."; pwd)
    echo "Exporting $WORKSPACE"
    docker run -it -v $WORKSPACE:/workspace -v $CWD/:/tools --rm "w3dconverter:dev" /tools/bash.sh $@
fi
