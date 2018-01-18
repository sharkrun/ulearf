#! /bin/sh

workroot=/opt/cluster

echo "===================> set ENV"
sed -i -e 's|"etcd_host":"ETCD_HOST",|"etcd_host":"'$ETCD_HOST'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"etcd_port":"ETCD_PORT",|"etcd_port":'$ETCD_PORT',|' /opt/cluster/conf/config.conf
sed -i -e 's|"etcd_allow_reconnect":"ETCD_ALLOW_RECONNECT",|"etcd_allow_reconnect":"'$ETCD_ALLOW_RECONNECT'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"etcd_protocol":"ETCD_PROTOCOL",|"etcd_protocol":"'$ETCD_PROTOCOL'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"deploy_server_addr":"DEPLOY_SERVER_ADDR",|"deploy_server_addr":"'$DEPLOY_SERVER_ADDR'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"user_server_addr":"USER_SERVER_ADDR",|"user_server_addr":"'$USER_SERVER_ADDR'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"cluster_auth_info_host":"CLUSTER_AUTH_INFO_HOST",|"cluster_auth_info_host":"'$CLUSTER_AUTH_INFO_HOST'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"cluster_auth_info_port":"CLUSTER_AUTH_INFO_PORT",|"cluster_auth_info_port":"'$CLUSTER_AUTH_INFO_PORT'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"apply_info_host":"APPLY_INFO_HOST",|"apply_info_host":"'$APPLY_INFO_HOST'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"apply_info_port":"APPLY_INFO_PORT",|"apply_info_port":"'$APPLY_INFO_PORT'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"current_host":"CURRENT_HOST",|"current_host":"'$CURRENT_HOST'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"uflow_host":"UFLOW_HOST",|"uflow_host":"'$UFLOW_HOST'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"ufleet_hosts":"UFLEET_HOSTS",|"ufleet_hosts":"'$UFLEET_HOSTS'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"vespace_manager_addr":"STORAGE_HOST",|"vespace_manager_addr":"'$STORAGE_HOST'",|' /opt/cluster/conf/config.conf
sed -i -e 's|"external_storage_image":"EXTERNAL_STORAGE_IMAGE",|"external_storage_image":"'$EXTERNAL_STORAGE_IMAGE'",|' /opt/cluster/conf/config.conf

if [ ! -d "$workroot/trace/logs" ]; then
  mkdir -p $workroot/trace/logs
fi

cd $workroot

export PYTHONPATH="."
./cluster >$workroot/trace/logs/main.out 2>&1
echo "--------------exited---------------"