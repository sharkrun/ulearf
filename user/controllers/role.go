package controllers

import ( //"encoding/json"
	//"errors"
	//"log"
	//"ufleet/user/auth"
	//"ufleet/user/models"
	"ufleet/user/role"
	//"ufleet/user/user"
	//"ufleet/user/util/userclient"
)

// Operations about Role
type RoleController struct {
	baseController
}

// @Title Get Group Role List info
// @Description get role list
// @Success 200 {object} []role.Role
// @Failure 500 {object} models.ErrorMsg
// @router / [get]
func (u *RoleController) Get() {
	u.NeedLogin("")
	u.Data["json"] = role.RoleList
	u.ServeJSON()
}
