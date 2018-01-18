# ETCD 配置

### 下载ETCD

Linux
```
ETCD_VER=v3.1.1
DOWNLOAD_URL=https://github.com/coreos/etcd/releases/download
curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
mkdir -p /tmp/test-etcd && tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/test-etcd --strip-components=1

/tmp/test-etcd/etcd --version

Git SHA: ac1c7eb
Go Version: go1.7.5
Go OS/Arch: linux/amd64

```

Mac OS (Darwin)
```
ETCD_VER=v3.1.1
DOWNLOAD_URL=https://github.com/coreos/etcd/releases/download
curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-darwin-amd64.zip -o /tmp/etcd-${ETCD_VER}-darwin-amd64.zip
mkdir -p /tmp/test-etcd && unzip /tmp/etcd-${ETCD_VER}-darwin-amd64.zip -d /tmp && mv /tmp/etcd-${ETCD_VER}-darwin-amd64/* /tmp/test-etcd

/tmp/test-etcd/etcd --version

```

### 启动ETCD

```
# start a local etcd server
/tmp/test-etcd/etcd

# write,read to etcd
ETCDCTL_API=3 /tmp/test-etcd/etcdctl --endpoints=localhost:2379 put foo "bar"
ETCDCTL_API=3 /tmp/test-etcd/etcdctl --endpoints=localhost:2379 get foo
```

### Docker 
```
docker run --net=host \
    --name etcd-v3.1.1 \
    --volume=/tmp/etcd-data:/etcd-data \
    quay.io/coreos/etcd:v3.1.1 \
    /usr/local/bin/etcd \
    --name my-etcd-1 \
    --data-dir /etcd-data \
    --listen-client-urls http://0.0.0.0:2379 \
    --advertise-client-urls http://0.0.0.0:2379 \
    --listen-peer-urls http://0.0.0.0:2380 \
    --initial-advertise-peer-urls http://0.0.0.0:2380 \
    --initial-cluster my-etcd-1=http://0.0.0.0:2380 \
    --initial-cluster-token my-etcd-token \
    --initial-cluster-state new \
    --auto-compaction-retention 1

docker exec etcd-v3.1.1 /bin/sh -c "export ETCDCTL_API=3 && /usr/local/bin/etcd -version"
docker exec etcd-v3.1.1 /bin/sh -c "export ETCDCTL_API=3 && /usr/local/bin/etcdctl version"
docker exec etcd-v3.1.1 /bin/sh -c "export ETCDCTL_API=3 && /usr/local/bin/etcdctl endpoint health"

docker exec etcd-v3.1.1 /bin/sh -c "export ETCDCTL_API=3 && /usr/local/bin/etcdctl put foo bar"
docker exec etcd-v3.1.1 /bin/sh -c "export ETCDCTL_API=3 && /usr/local/bin/etcdctl get --consistency=s foo"
```