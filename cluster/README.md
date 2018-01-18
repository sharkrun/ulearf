
### 安装依赖库

centos

```
$ yum install gcc swig python-devel libffi-devel pycurl
$ pip install -r requirements.txt
```

ubuntu

```
sudo apt-get install gcc swig python-dev libffi-dev pycurl 

$ pip install -r requirements.txt
```

#### 部署流程
$ ./build.sh
$ docker-compose build
$ docker-compose up -d

### 运行单元测试
python unitest.py


### ETCD 配置

参考[ETCD](ETCD.md)


###
初始化数据：
    在upgrade下的data.py中

###  项目结构
    swagger:
        swagger所在目录
    src:
        项目的核心目录
        src/api：
            api接口
        src/common:
            通用的函数方法
        src/core:
            twisted server相关配置
        src/etcddb:
            etcd数据库操作
        src/frame:
            配置文件（etcd的配置，服务的配置，logging的配置等）

        src/robot:
            robotframework测试用例
        src/test:
            接口单元测试用例
        src/trace:
            日志所在目录
        src/upgrade:
            初始化数据库
            
# 升级基础镜像的方法
    1. 修改基础镜像yaml文件： Dockerfile.build
    2. 构建镜像: docker build  -t cluster-base . -f Dockerfile.build
    3. 给镜像打标签: docker tag
    3. 登录私有仓库： docker login 192.168.18.250:5002
    4. push镜像： docker push <镜像id>