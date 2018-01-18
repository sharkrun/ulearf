package usergroup

import (
	"ufleet/user/role"
	"ufleet/user/user"
	etcd "ufleet/user/util/etcdclientv3"

	"github.com/astaxie/beego"
)

// Group indicate the base group of ufleet product, all other kind of group base on group
type Group struct {
	Name string `json:"name"`
}

// UserGroup usergroup
type UserGroup struct {
	Name       string `json:"name"`
	Describe   string `json:"describe"`
	CreateTime int64  `json:"createtime"`
	UserCount  int    `json:"usercount"`
}

// GroupUser to join group, role, user together
type GroupUser struct {
	Role     *role.Role     `json:"role"`
	Group    *UserGroup     `json:"-"`
	User     *user.User     `json:"-"`
	ShowUser *user.ShowUser `json:"user"`
}

// GroupUserAdd add user to group
type GroupUserAdd struct {
	Username  string `json:"username"`
	Rolename  string `json:"role"`
	Groupname string `json:"-"`
	UserId    string `json:"uid"`
}

var (
	etcdKeyBase = beego.AppConfig.String("etcdbase")

	usergroupKeyBase   = etcd.EtcdPathJoin([]string{etcdKeyBase, "usergroup"})
	usergroupDetailKey = "info"

	groupKeyBase      = etcd.EtcdPathJoin([]string{etcdKeyBase, "group"})
	groupUserGroupKey = "user-group"

	groupuserKey = "user"
	userroleKey  = "role"
)
