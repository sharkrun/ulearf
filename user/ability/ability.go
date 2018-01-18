package ability

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/astaxie/beego"

	"ufleet/user/util/logs"

	etcd "ufleet/user/util/etcdclientv3"

	"ufleet/user/util/request"
)

type Ability struct {
	Object  string   `json:"object"`
	Operate []string `json:"operate"`
}

type RoleAbility struct {
	Role        string    `json:"role"`
	AbilityList []Ability `json:"ability"`
}

var (
	etcdKeyBase               = beego.AppConfig.String("etcdbase")
	abilityKeyBase            = etcd.EtcdPathJoin([]string{etcdKeyBase, beego.AppConfig.String("etcdabilityconfig")})
	AbilityList    []*Ability = make([]*Ability, 0)
)

func InitAbility() {
	abi_info, _ := etcd.Client.GetKV(abilityKeyBase)

	AbilityList, _ = AbilityListFromJson(abi_info)

	readAbilityFromModule()

	logs.Info("update ablity list", AbilityList)
	abi_info, _ = AbilityListToJson(AbilityList)
	logs.Info("ablity to json", abi_info)

	err := etcd.Client.SetKV(abilityKeyBase, abi_info)
	if err != nil {
		logs.Warn("set to etcd fail", abilityKeyBase, abi_info)
	}

}

//各模块的ability接口
func readAbilityFromModule() []*Ability {
	abilityEndpoints := os.Getenv("MODULE_ENDPOINTS")
	abi_endpoints := strings.Split(abilityEndpoints, ",")
	logs.Info("read ability from module ", abi_endpoints)
	var find bool
	for _, k := range abi_endpoints {
		abi_info, err := request.MakeRequest(k+"/v1/ability", "GET", nil, "")
		if err != nil {
			logs.Warn("get ability from module  %v fail for %v", k, err)
			continue
		}

		abi_list, err2 := AbilityListFromJson(abi_info)
		if err2 != nil {
			logs.Warn("unmarshal data to  ability from module  %v fail for %v", k, err2)
			continue
		}
		find = false
		for _, abi := range abi_list {
			for _, rabi := range AbilityList {
				if abi.Object == rabi.Object {
					rabi.Operate = abi.Operate
					find = true
				}
			}
			if find == false {
				AbilityList = append(AbilityList, abi)
			}
		}
	}
	logs.Info("read ability from module:", AbilityList)
	return AbilityList
}

func (a *Ability) ToJson() (string, error) {
	b, err := json.Marshal(a)
	if err != nil {
		logs.Warn("transfer ability struct ", a, " to string fail", err)
		return "", err
	}
	return string(b), nil
}

func (a *Ability) FromJson(b string) error {
	if err := json.Unmarshal([]byte(b), &a); err != nil {
		logs.Warn("transfer ability json string ", b, " to struct fail", err)
		return fmt.Errorf("transfer ability string %s to struct fail", b)
	}
	return nil
}

func (a *Ability) Equal(b *Ability) bool {
	if a.Object != b.Object {
		return false
	}
	if len(a.Operate) != len(b.Operate) {
		return false
	}
	var i1 []interface{} = make([]interface{}, len(a.Operate))
	var i2 []interface{} = make([]interface{}, len(b.Operate))
	for i, d := range a.Operate {
		i1[i] = d
	}
	for i, d := range b.Operate {
		i2[i] = d
	}
	if SliceEqaul(i1, i2) == false {
		return false
	}
	return true
}

func AbilityListToJson(list []*Ability) (string, error) {
	b, err := json.Marshal(list)
	if err != nil {
		logs.Warn("transfer ability list ", list, " to string fail", err)
		return "", err
	}
	return string(b), nil
}

func AbilityListFromJson(j string) ([]*Ability, error) {
	var l []*Ability = make([]*Ability, 0)
	if err := json.Unmarshal([]byte(j), &l); err != nil {
		return l, err
	}
	return l, nil
}

func RoleAbilityListToJson(list []*RoleAbility) (string, error) {
	b, err := json.Marshal(list)
	if err != nil {
		logs.Warn("transfer role ability list ", list, " to string fail", err)
		return "", err
	}
	return string(b), nil
}

func RoleAbilityListFromJson(j string) ([]*RoleAbility, error) {
	var l []*RoleAbility = make([]*RoleAbility, 0)
	if err := json.Unmarshal([]byte(j), &l); err != nil {
		return l, err
	}
	return l, nil
}

func InSlice(val interface{}, slice []interface{}) bool {
	for _, v := range slice {
		if v == val {
			return true
		}
	}
	return false
}

func SliceEqaul(slice1, slice2 []interface{}) bool {
	if len(slice1) != len(slice2) {
		return false
	}
	for _, v := range slice1 {
		if !InSlice(v, slice2) {
			return false
		}
	}
	return true
}
