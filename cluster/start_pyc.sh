#! /bin/sh

workroot=/opt/source

echo "===================> set ENV"
sed -i -e 's|"etcd_host":"ETCD_HOST",|"etcd_host":"'$ETCD_HOST'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"etcd_port":"ETCD_PORT",|"etcd_port":'$ETCD_PORT',|' /opt/source/frame/conf/config.conf
sed -i -e 's|"etcd_allow_reconnect":"ETCD_ALLOW_RECONNECT",|"etcd_allow_reconnect":"'$ETCD_ALLOW_RECONNECT'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"etcd_protocol":"ETCD_PROTOCOL",|"etcd_protocol":"'$ETCD_PROTOCOL'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"deploy_server_addr":"DEPLOY_SERVER_ADDR",|"deploy_server_addr":"'$DEPLOY_SERVER_ADDR'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"user_server_addr":"USER_SERVER_ADDR",|"user_server_addr":"'$USER_SERVER_ADDR'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"cluster_auth_info_host":"CLUSTER_AUTH_INFO_HOST",|"cluster_auth_info_host":"'$CLUSTER_AUTH_INFO_HOST'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"cluster_auth_info_port":"CLUSTER_AUTH_INFO_PORT",|"cluster_auth_info_port":"'$CLUSTER_AUTH_INFO_PORT'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"apply_info_host":"APPLY_INFO_HOST",|"apply_info_host":"'$APPLY_INFO_HOST'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"apply_info_port":"APPLY_INFO_PORT",|"apply_info_port":"'$APPLY_INFO_PORT'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"current_host":"CURRENT_HOST",|"current_host":"'$CURRENT_HOST'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"uflow_host":"UFLOW_HOST",|"uflow_host":"'$UFLOW_HOST'",|' /opt/source/frame/conf/config.conf
sed -i -e 's|"ufleet_hosts":"UFLEET_HOSTS",|"ufleet_hosts":"'$UFLEET_HOSTS'",|' /opt/source/frame/conf/config.conf


if [ ! -d "$workroot/trace/logs" ]; then
  mkdir -p $workroot/trace/logs
fi

cd $workroot

export PYTHONPATH="."
PROCESS_NUM=`ps -ef | grep "python $workroot/main" | grep -v "grep" | wc -l`
if [ $PROCESS_NUM -gt 0 ];
then
    echo "the Service is already running!"
    exit 1
else
    if [ -f "$workroot/main.pyc" ]; then
        python $workroot/main.pyc >$workroot/trace/logs/main.out 2>&1
    else
        python $workroot/main.py >$workroot/trace/logs/main.out 2>&1
    fi
    echo "--------------exited---------------"
fi
