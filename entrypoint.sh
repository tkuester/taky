#!/usr/bin/env bash

if ! command -v taky &> /dev/null
then
	echo "#### installing dev python package ####"
	python setup.py develop
fi

if [ ! -f "/etc/taky/taky.conf" ]; then
    echo '### running taky setup ####'
	takyctl setup --public-ip 1.2.3.4
fi

echo '#### starting taky ####'
supervisord -c /etc/supervisor/conf.d/supervisord.conf
