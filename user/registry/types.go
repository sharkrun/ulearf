package registry

import (
	etcd "ufleet/user/util/etcdclientv3"

	"github.com/astaxie/beego"
)

const (
	PUBLIC_REGISTRY = "-"
)

var (
	etcdKeyBase     = beego.AppConfig.String("etcdbase")
	registryKeyBase = etcd.EtcdPathJoin([]string{etcdKeyBase, "registry"})
)

//Registry save docker registry
type Registry struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	Address    string `json:"address"`
	User       string `json:"user"`
	Password   string `json:"password"`
	Email      string `json:"email,omitempty"`
	Extend     string `json:"extend,omitempty"`
	UpdateTime int    `json:"updateTime"`
	Belong     string `json:"belong,omitempty"`
}
