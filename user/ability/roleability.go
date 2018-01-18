package ability

import (
	//"encoding/json"
	//"fmt"

	"fmt"
	"os"
	"strings"

	//"ufleet/user/ability"
	"ufleet/user/role"
	etcd "ufleet/user/util/etcdclientv3"
	"ufleet/user/util/logs"
	"ufleet/user/util/request"
)

var (
	//	etcdKeyBase                          = beego.AppConfig.String("etcdbase")
	//	ablityKeyBase                        = etcd.EtcdPathJoin([]string{etcdKeyBase, beego.AppConfig.String("etcdabilityconfig")})
	RoleAbilityList []*RoleAbility = make([]*RoleAbility, 0)
)

//检测role ability是否匹配

func InitRoleAbility() {
	abi_info, err := etcd.Client.GetKV(abilityKeyBase)
	if err != nil {
		logs.Warn(fmt.Errorf("get ability info from %v for %v ", abilityKeyBase, err))
	}

	RoleAbilityList, err = RoleAbilityListFromJson(abi_info)
	if err != nil {
		logs.Warn(fmt.Errorf("RoleAbilityListToJson fail for %v", err))
	}

	readRoleAbilityFromModule()

	logs.Info("update role ability list", RoleAbilityList)
	abi_info, _ = RoleAbilityListToJson(RoleAbilityList)
	logs.Info("role ability to json", abi_info)

	err = etcd.Client.SetKV(abilityKeyBase, abi_info)
	if err != nil {
		logs.Warn(fmt.Sprintf("set to etcd key %v fail for %v", abilityKeyBase, err))
	}

}

//检测角色ability的操作是否合法
func isOperateValid(roleOperate []string, abilityOperate []string) bool {
	for _, v := range roleOperate {
		found := false
		for _, j := range abilityOperate {

			if v == j {
				found = true
				break
			}
		}

		if found {
			continue
		}

		logs.Warn(fmt.Sprintf("ability %v  can not find in ability list "))
		return false

	}

	return true
}

func checkRoleAbilityValid(abi_list []*RoleAbility) error {
	for _, v := range abi_list {

		if !role.IsValidRole(v.Role) {
			return fmt.Errorf("role \"%v\" is not valid", v.Role)
		}

		for _, j := range v.AbilityList {

			found := false
			for _, i := range AbilityList {
				if i.Object == j.Object {
					found = true
					if !isOperateValid(j.Operate, i.Operate) {
						return fmt.Errorf("ability %v in role %v have invalid Operate", i.Object, v.Role)
					}
				}
			}

			if !found {
				return fmt.Errorf("ability %v in role %v is invalid", j.Object, v.Role)
			}
		}
	}
	return nil
}

func readRoleAbilityFromModule() []*RoleAbility {
	abilityEndpoints := os.Getenv("MODULE_ENDPOINTS")
	abi_endpoints := strings.Split(abilityEndpoints, ",")
	logs.Info("======>read role ability from module ", abi_endpoints)

	for _, k := range abi_endpoints {
		logs.Info("======>start to read role ability from module ", k)
		abi_info, err := request.MakeRequest(k+"/v1/abilityinit", "GET", nil, "")
		if err != nil {
			logs.Warn("get role ability from module  %v fail for %v", k, err)
			continue
		}

		abi_list, err2 := RoleAbilityListFromJson(abi_info)
		if err2 != nil {
			logs.Warn("unmarshal data to role ability from module  %v fail for %v", k, err2)
			continue
		}

		//检测Role权限和所有权限拿对比,看是不是有错误的权限
		err = checkRoleAbilityValid(abi_list)
		if err != nil {
			logs.Warn(fmt.Errorf("module %v have invalid role ability : %v", k, err))
			continue
		}

		//这里需要加锁
		logs.Info("====>", abi_list)
		RoleAbilityList = make([]*RoleAbility, len(abi_list))
		copy(RoleAbilityList, abi_list)

		logs.Info("====>", RoleAbilityList)

		/*
			find = false
			for _, abi := range abi_list {
				for _, rabi := range RoleAbilityList {
					if abi.Object == rabi.Object {
						rabi.Operate = abi.Operate
						find = true
					}
				}
				if find == false {
					RoleAbilityList = append(RoleAbilityList, abi)
				}
			}
		*/

	}
	logs.Info("read ability from module:", RoleAbilityList)
	return RoleAbilityList
}

func GetRoleAbility(roleName string) []Ability {
	for _, v := range RoleAbilityList {
		if v.Role == roleName {
			return v.AbilityList
		}
	}
	return nil
}
