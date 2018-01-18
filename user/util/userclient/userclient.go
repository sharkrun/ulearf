package userclient

import (
	"encoding/json"
	//"errors"
	"fmt"
	"net/http"
	"strings"

	"ufleet/user/ability"
	"ufleet/user/role"
	"ufleet/user/user"
	"ufleet/user/usergroup"
	"ufleet/user/util/request"
)

func UserVerifyAndGet(token string, endpoint string) (*user.User, error) {
	url := strings.TrimRight(endpoint, "/") + "/v1/user/verify/" + strings.TrimRight(token, " /")
	method := "GET"

	ret_json_str, err := request.MakeRequest(url, method, nil, "")
	if err != nil {
		return nil, fmt.Errorf("token %s verify fail", token)
	}

	auser := &user.User{}
	json.Unmarshal([]byte(ret_json_str), auser)
	return auser, nil
}

func UserGetById(id string, token string, endpoint string) (*user.User, error) {
	url := strings.TrimRight(endpoint, "/") + "/v1/user/" + strings.TrimRight(id, " /")

	method := "GET"

	headers := make(map[string]string)
	headers["Token"] = token

	retJSONStr, err := request.MakeRequest(url, method, headers, "")
	if err != nil {
		return nil, err
	}

	auser := new(user.User)
	json.Unmarshal([]byte(retJSONStr), auser)
	return auser, nil
}

func GetUserByRequest(req *http.Request, endpoint string) (*user.User, error) {
	token, ok := req.Header["Token"]
	if !ok {
		return nil, fmt.Errorf("No token in request")
	}
	u, err := UserVerifyAndGet(token[0], endpoint)
	if err != nil {
		return nil, err
	}
	return u, nil
}

func GetUser(token, endpoint string) (*user.User, error) {
	return UserVerifyAndGet(token, endpoint)
}

func CheckUserIsSuperAdmin(req *http.Request, endpoint string) (bool, error) {
	u, err := GetUserByRequest(req, endpoint)
	if err != nil {
		return false, err
	}
	if u.IsSuperAdmin() == false {
		return false, nil
	} else {
		return true, nil
	}
}

func CheckUserIsSuperAdminByToken(endpoint string, token string) (bool, error) {
	method := "Get"
	url := ""
	req, err := http.NewRequest(method, url, nil)
	if err != nil {
		return false, err
	}
	req.Header.Set("Token", token)
	return CheckUserIsSuperAdmin(req, endpoint)
}

func UserRoleGetByToken(groupname string, token string, endpoint string) (*role.Role, error) {
	headers := make(map[string]string)
	headers["Token"] = token

	method := "GET"

	u, err := UserVerifyAndGet(token, endpoint)
	if err != nil {
		return nil, err
	}

	url := strings.TrimRight(endpoint, "/") + "/v1/usergroup/" + strings.TrimRight(groupname, " /") + "/user/" + strings.Trim(u.ID, " /")

	retJSONStr, err := request.MakeRequest(url, method, headers, "")
	if err != nil {
		return nil, err
	}

	aguser := new(usergroup.GroupUser)
	json.Unmarshal([]byte(retJSONStr), aguser)
	return aguser.Role, nil

}

func GetUserRoleByRequest(req *http.Request, u *user.User, groupname, endpoint string) (*role.Role, error) {
	token, ok := req.Header["Token"]
	if !ok {
		return nil, fmt.Errorf("No token in request")
	}
	return UserRoleGetByToken(groupname, token[0], endpoint)
}

func GetUserAndRoleByRequest(req *http.Request, groupname, endpoint string) (*user.User, *role.Role, error) {

	u, err := GetUserByRequest(req, endpoint)
	if err != nil {
		return nil, nil, err
	}
	if u.IsSuperAdmin() {
		return u, role.SuperAdmin, nil
	}

	if u.IsAdmin() {
		return u, role.Admin, nil
	}

	r, err1 := GetUserRoleByRequest(req, u, groupname, endpoint)
	if err1 != nil {
		return nil, nil, err1
	}
	return u, r, nil
}

func GetRoleAbility(endpoint string, roleName string) ([]ability.Ability, error) {
	url := strings.TrimRight(endpoint, "/") + "/v1/ability"
	headers := make(map[string]string)
	method := "GET"

	retJSONStr, err := request.MakeRequest(url, method, headers, "")
	if err != nil {
		return []ability.Ability{}, err
	}

	abis := make([]ability.Ability, 0)
	err = json.Unmarshal([]byte(retJSONStr), &abis)
	if err != nil {
		return []ability.Ability{}, err
	}

	return abis, nil
}

func CheckRoleOperateAllowed(endpoint string, token string, groupName string, object string, operate string) (bool, error) {

	if len(endpoint) == 0 || len(token) == 0 || len(object) == 0 || len(operate) == 0 {
		return false, fmt.Errorf("must provide valid args for check privilege")
	}

	yes, err := CheckUserIsSuperAdminByToken(endpoint, token)
	if err != nil {
		return false, err
	}

	//超级管理员，具有所有权限
	if yes {
		return true, nil
	}

	if len(groupName) == 0 {
		return false, fmt.Errorf("must provide valid project name")
	}

	role, err := UserRoleGetByToken(groupName, token, endpoint)
	if err != nil {
		return false, err
	}

	rabis, err := GetRoleAbility(endpoint, role.Role)
	if err != nil {
		return false, err
	}

	for _, v := range rabis {
		if v.Object == object {
			for _, j := range v.Operate {
				if j == operate {
					return true, nil
				}

			}
		}
	}

	return false, nil
}
