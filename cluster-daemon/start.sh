#! /bin/sh

workroot=/opt/cluster-daemon

echo "===================> set ENV"
sed -i -e 's|"current_host":"CURRENT_HOST",|"current_host":"'$CURRENT_HOST'",|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"ufleet_ui_port":"UFLEET_UI_PORT",|"ufleet_ui_port":"'$UFLEET_UI_PORT'",|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"etcd_host":"ETCD_HOST",|"etcd_host":"'$ETCD_HOST'",|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"etcd_port":"ETCD_PORT",|"etcd_port":'$ETCD_PORT',|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"etcd_allow_reconnect":"ETCD_ALLOW_RECONNECT",|"etcd_allow_reconnect":"'$ETCD_ALLOW_RECONNECT'",|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"etcd_protocol":"ETCD_PROTOCOL",|"etcd_protocol":"'$ETCD_PROTOCOL'",|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"cluster_auth_info_host":"CLUSTER_AUTH_INFO_HOST",|"cluster_auth_info_host":"'$CLUSTER_AUTH_INFO_HOST'",|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"cluster_auth_info_port":"CLUSTER_AUTH_INFO_PORT",|"cluster_auth_info_port":"'$CLUSTER_AUTH_INFO_PORT'",|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"apply_info_host":"APPLY_INFO_HOST",|"apply_info_host":"'$APPLY_INFO_HOST'",|' /opt/cluster-daemon/conf/config.conf
sed -i -e 's|"apply_info_port":"APPLY_INFO_PORT",|"apply_info_port":"'$APPLY_INFO_PORT'",|' /opt/cluster-daemon/conf/config.conf


if [ ! -d "$workroot/trace/logs" ]; then
  mkdir -p $workroot/trace/logs
fi

cd $workroot

export PYTHONPATH="."
./cluster-daemon >$workroot/trace/logs/main.out 2>&1
echo "--------------exited---------------"
