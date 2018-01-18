package role

import (
	"encoding/json"
	"fmt"

	"github.com/astaxie/beego"

	etcd "ufleet/user/util/etcdclientv3"
)

const (
	ROLE_SUPERADMIN  = "superadmin"
	ROLE_ADMIN       = "admin"
	ROLE_GROUP_ADMIN = "group_admin"
	ROLE_GROUP_USER  = "group_user"
)

type Role struct {
	Role       string `json:"role"`
	RoleENname string `json:"role_name"`
	RoleCNname string `json:"cn_name"`
}

var (
	etcdKeyBase = beego.AppConfig.String("etcdbase")
	roleKeyBase = etcd.EtcdPathJoin([]string{etcdKeyBase, beego.AppConfig.String("etcdroleconfig")})
)

var SuperAdmin *Role = &Role{ROLE_SUPERADMIN, "Superadmin", "超级管理员"}
var Admin *Role = &Role{ROLE_ADMIN, "Admin", "管理员"}
var GroupAdmin *Role = &Role{ROLE_GROUP_ADMIN, "Group Admin", "分组管理员"}
var GroupUser *Role = &Role{ROLE_GROUP_USER, "Group User", "分组用户"}
var RoleList []*Role = []*Role{SuperAdmin, Admin, GroupAdmin, GroupUser}

func InitRole() {
	var k, v string
	rolelist := etcd.Client.ListDir(roleKeyBase)
	if len(rolelist) == 0 {
		for _, r := range RoleList {
			k = etcd.EtcdPathJoin([]string{roleKeyBase, r.Role, "info"})
			v = r.ToJSON()
			etcd.Client.SetKV(k, v)
		}
	}
}

func (r *Role) ToJSON() string {
	j, err := json.Marshal(r)
	if err != nil {
		return ""
	}
	return string(j)
}

func (r *Role) FromJSON(jsonStr string) error {
	json.Unmarshal([]byte(jsonStr), r)
	var find = false
	for _, rl := range RoleList {
		if r.Role == rl.Role {
			r = rl
			find = true
			break
		}
	}
	if find == false {
		return fmt.Errorf("Get unkown role:%s", r.Role)
	}
	return nil
}

func (r *Role) IsGroupAdmin() bool {
	if r.Role == ROLE_GROUP_ADMIN {
		return true
	}
	return false
}

func (r *Role) IsGroupUser() bool {
	if r.Role == ROLE_GROUP_USER {
		return true
	}
	return false
}

func (r *Role) IsSuperAdmin() bool {
	if r.Role == ROLE_SUPERADMIN {
		return true
	}
	return false
}

func (r *Role) IsAdmin() bool {
	if r.Role == ROLE_ADMIN {
		return true
	}
	return false
}

func GetRoleByRolename(rolename string) *Role {
	for _, r := range RoleList {
		if rolename == r.Role {
			return r
		}
	}
	return nil
}

func IsValidRole(rolename string) bool {
	if rolename == ROLE_SUPERADMIN || rolename == ROLE_ADMIN || rolename == ROLE_GROUP_ADMIN || rolename == ROLE_GROUP_USER {
		return true
	}
	return false
}
