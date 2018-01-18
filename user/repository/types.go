package repository

import (
	etcd "ufleet/user/util/etcdclientv3"

	"github.com/astaxie/beego"
)

var (
	etcdKeyBase       = beego.AppConfig.String("etcdbase")
	repositoryKeyBase = etcd.EtcdPathJoin([]string{etcdKeyBase, "repository"})
)

//Registry save docker registry
type Repository struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	Address    string `json:"address"`
	Token      string `json:"token"`
	Type       string `json:"type"`
	UpdateTime int    `json:"updateTime"`
}
