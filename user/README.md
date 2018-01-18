# 用户模块


[设计说明](用户及认证模块设计说明.md)


## 代码检出及本地调试

在 $GOPATH/src 下创建 ufleet 文件夹. 在 ufleet 文件夹下 clone 本代码库代码 `git clone http://192.168.19.250/ufleet/user.git`, 确保代码放置方式为 $GOPATH/src/ufleet/user/README.md

本地编译运行依照如下步骤:

1. 下载 beego :`go get github.com/astaxie/beego`
2. 启动 etcd : `etcd --listen-client-urls http://0.0.0.0:2379 --advertise-client-urls http://192.168.3.42:2379,http://localhost:2379`
3. 设置环境变量 : `export ETCDCLUSTER=http://127.0.0.1:2379`
4. 在 user 目录下启动系统 : `bee run -gendoc=true -downdoc=true`

## 编译打包流程

### 编译准备

准备编译环境：通过执行 `./script/prepare-build-image.sh` 生成编译环境镜像，镜像名默认为 `ufleet-user-build:latest`，或直接使用golang:1.6或golang:1.7镜像做为编译环境。

### 编译

使用编译环境进行编译 ：通过执行 `./script/docker-build.sh` 启动一个容器并在容器内通过执行 `build.sh` 脚本完成编译。`build.sh` 会将自身文件夹链接到系统的$GOPATH/src 下，然后在目录中执行 go build，因此要求编译环境中有 golang 相关环境。实际编译内容为二进制文件 cicd_user，默认会保存在代码根目录。

### 打包

生成镜像：通过执行 `./script/package.sh` 或在代码根目录下执行 `docker build -f Dockerfile -t ufleet-user .` 完成镜像生成。

## 运行流程

### etcd准备及环境变量设置

启动 etcd 或 etcd 集群,确保能正确连接. 在 user 模块运行的环境中设置环境变量 ETCDCLUSTER, 并直接运行 user 模
块. 如不设置此环境变量, 默认参数为 http://127.0.0.1:2379

### 运行模块

直接运行编译好的 user 模块即可.启动后应用程序监听端口为 8881. 可通过 /swagger 访问 api 接口界面。
