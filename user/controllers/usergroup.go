package controllers

import (
	"encoding/json"

	//"ufleet/user/auth"

	"ufleet/user/models"
	"ufleet/user/registry"
	"ufleet/user/role"
	"ufleet/user/user"
	"ufleet/user/usergroup"
	"ufleet/user/util/broadcast"
	"ufleet/user/util/logs"
)

//UserGroupController Operations about UserGroup
type UserGroupController struct {
	baseController
}

// @Title Get All UserGroup
// @Description get all usergroup info
// @Param	token			header	string			true		"The login token"
// @Success 200 {object} []usergroup.UserGroup
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router / [get]
func (p *UserGroupController) GetAll() {
	p.NeedLogin("")
	loginUser := p.User
	userGroups := []usergroup.UserGroup{}
	// 2017-04-18 edit by robin zhiqiang.li@youruncloud.com
	// groupUser := usergroup.GroupUser{}
	// err := groupUser.GetByName(loginUser.Username)
	if loginUser.HasAdminPower() {
		p.Data["json"] = usergroup.GetUserGroups()
	} else {
		getUserGroups := p.User.GetUserGroup()
		for _, uGroup := range getUserGroups {
			userGroup, err := usergroup.GetUserGroup(uGroup)
			if err == nil {
				userGroups = append(userGroups, userGroup)
			}
		}
		p.Data["json"] = userGroups
	}
	p.ServeJSON()
}

// @Title Gets all the user groups that the user belongs to
// @Description Gets all the user groups that the user belongs to
// @Param	token			header	string			true		"The login token"
// @Success 200 {object} []usergroup.UserGroup
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router / [get]
func (p *UserGroupController) GetMyGroup() {
	p.NeedLogin("")
	userGroups := []usergroup.UserGroup{}

	getUserGroups := p.User.GetUserGroup()
	for _, uGroup := range getUserGroups {
		userGroup, err := usergroup.GetUserGroup(uGroup)
		if err == nil {
			userGroups = append(userGroups, userGroup)
		}
	}
	p.Data["json"] = userGroups

	p.ServeJSON()
}

// @Title Add UserGroup
// @Description add usergroup
// @Param	body			body 	usergroup.UserGroup		true		"usergroup to add"
// @Param	token			header	string					true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router / [post]
func (p *UserGroupController) Post() {
	p.NeedAdmin("Higher than admin can add group")

	addg := new(usergroup.UserGroup)
	json.Unmarshal(p.Ctx.Input.RequestBody, addg)

	if err := addg.Add(); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	p.LogAdd(4, "创建用户组[", addg.Name, "]成功")

	p.Data["json"] = models.GenerateResponseMsg("Add success")
	p.ServeJSON()
}

// @Title Modify UserGroup
// @Description modify usergroup
// @Param	groupname		path 	string					true		"group name"
// @Param	body			body 	usergroup.UserGroup		true		"usergroup to modify"
// @Param	token			header	string					true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:groupname [put]
func (p *UserGroupController) Put() {
	groupname := p.GetString(":groupname")
	p.NeedGroupAdmin(groupname, "Only group admin or superadmin can modify group")

	modifyg := new(usergroup.UserGroup)
	json.Unmarshal(p.Ctx.Input.RequestBody, modifyg)
	if modifyg.Name != groupname {
		msg := models.GenerateErrorMsg(500, "UserGroup name does not match")
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	if err := modifyg.Update(); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	p.LogMod(4, "修改用户组[", modifyg.Name, "]信息成功")

	p.Data["json"] = models.GenerateResponseMsg("Modify success")
	p.ServeJSON()
}

// @Title Get UserGroup
// @Description get usergroup info
// @Param	groupname		path 	string			true		"group name"
// @Param	token			header	string			true		"The login token"
// @Success 200 {object} usergroup.UserGroup
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:groupname [get]
func (p *UserGroupController) Get() {
	p.NeedLogin("")
	loginuser := p.User

	groupuser := new(usergroup.GroupUser)
	err := groupuser.GetByID(loginuser.ID, p.GetString(":groupname"))
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	// groupname := p.GetString(":groupname")
	// getg := new(usergroup.UserGroup)
	groupName := p.GetString(":groupname")
	userGroup := usergroup.UserGroup{}
	userGroup, err = usergroup.GetUserGroup(groupName)
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	// p.Data["json"] = getg
	p.Data["json"] = userGroup
	p.ServeJSON()
}

// @Title Delete UserGroup
// @Description delete usergroup
// @Param	groupname		path 	string			true		"group name"
// @Param	token			header	string			true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:groupname [delete]
func (p *UserGroupController) Delete() {
	p.NeedAdmin("Higher than admin can delete group")

	groupname := p.GetString(":groupname")
	delg := new(usergroup.UserGroup)
	delg.Name = groupname

	reg := registry.Registry{}
	err := reg.RemoveGroupReg(groupname)
	if err != nil {
		logs.Error("remove user all registry fail,as [", err, "]")
	}

	if err := delg.Delete(); err != nil {
		p.LogDel(2, "删除用户组[", groupname, "]失败,[", err.Error(), "]")
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	token, ok := p.Ctx.Request.Header["Token"]
	if ok {
		broadcast.DeleteGroup(token[0], groupname)
	}

	p.LogDel(4, "删除用户组[", groupname, "]成功")

	p.Data["json"] = models.GenerateResponseMsg("Delete success")
	p.ServeJSON()
}

// @Title Add User to UserGroup
// @Description add user to usergroup
// @Param	groupname		path 	string			true		"group name"
// @Param	body			body 	usergroup.GroupUserAdd		true		"to add user to group"
// @Param	token			header	string			true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:groupname/user [post]
func (p *UserGroupController) AddUser() {
	groupname := p.GetString(":groupname")
	p.NeedGroupAdmin(groupname, "Only group admin or superadmin can add group user")

	apu_info := new(usergroup.GroupUserAdd)
	json.Unmarshal(p.Ctx.Input.RequestBody, apu_info)
	apu_info.Groupname = groupname

	apu := new(usergroup.GroupUser)
	uu := new(user.User)

	if len(apu_info.Username) > 0 {
		if err := uu.GetByName(apu_info.Username); err != nil {
			msg := models.GenerateErrorMsg(500, err.Error())
			p.Ctx.ResponseWriter.WriteHeader(500)
			p.Data["json"] = msg
			p.ServeJSON()
			return
		}
	} else if len(apu_info.UserId) > 0 {
		if err := uu.GetByID(apu_info.UserId); err != nil {
			msg := models.GenerateErrorMsg(500, err.Error())
			p.Ctx.ResponseWriter.WriteHeader(500)
			p.Data["json"] = msg
			p.ServeJSON()
			return
		}
	} else {
		msg := models.GenerateErrorMsg(500, "No User info provided")
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	apu.User = uu

	if apu.Role = role.GetRoleByRolename(apu_info.Rolename); apu.Role == nil {
		msg := models.GenerateErrorMsg(500, "Group Role name error")
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	ug := new(usergroup.UserGroup)
	if err := ug.Get(apu_info.Groupname); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	apu.Group = ug

	if err := apu.AddToGroup(); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	p.LogAdd(4, " 添加 用户[", apu.User.Username, "]到用户组[", apu.Group.Name, "]成功")

	p.Data["json"] = models.GenerateResponseMsg("Add success")
	p.ServeJSON()
}

// @Title Get All UserGroup User
// @Description get all user of a group
// @Param	groupname		path 	string			true		"group name"
// @Param	token			header	string			true		"The login token"
// @Success 200 {object} []usergroup.GroupUser
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /allusers/:groupname [get]
func (p *UserGroupController) GetAllUser() {
	groupname := p.GetString(":groupname")
	p.NeedLogin("")
	// p.NeedGroupAdmin(groupname, "Only group admin or superadmin can get all group user")
	all_info, err := usergroup.GetAllUserInGroup(groupname)
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	p.Data["json"] = all_info
	p.ServeJSON()
}

// @Title Get Group User
// @Description get user of a usergroup
// @Param	groupname		path 	string			true		"group name"
// @Param	uid				path 	string			true		"user id"
// @Param	token			header	string			true		"The login token"
// @Success 200 {object} usergroup.GroupUser
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:groupname/user/:uid [get]
func (p *UserGroupController) GetUser() {
	groupname := p.GetString(":groupname")
	userid := p.GetString(":uid")

	p.NeedLogin("")
	loginuser := p.User

	groupuser := new(usergroup.GroupUser)
	err := groupuser.GetByID(loginuser.ID, groupname)
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	if groupuser.IsAdmin() == false && p.GetString(":uid") != loginuser.ID {
		msg := models.GenerateErrorMsg(403, "Only group admin or userself can get group user info")
		p.Ctx.ResponseWriter.WriteHeader(403)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	ggu := new(usergroup.GroupUser)

	if err := ggu.GetByID(userid, groupname); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	p.Data["json"] = ggu
	p.ServeJSON()
}

// @Title Get User's Group
// @Description get user's groups
// @Param	uid			path 	string			true		"user id"
// @Param	token		header	string			true		"The login token"
// @Success 200 {object} []string
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /user/:uid [get]
func (p *UserGroupController) GetGroup() {
	p.NeedLogin("")
	loginuser := p.User
	uid := p.GetString(":uid")

	if loginuser.HasAdminPower() == false && loginuser.ID != uid {
		msg := models.GenerateErrorMsg(500, "Only superadmin or userself can get user's group info")
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	u := new(user.User)
	pu := new(usergroup.GroupUser)
	if err := u.GetByID(uid); err != nil {
		msg := models.GenerateErrorMsg(404, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(404)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	pu.User = u
	p.Data["json"] = pu.GetAllGroupname()
	p.ServeJSON()
}

// @Title Modify Group User
// @Description modify user role in group
// @Param	groupname		path 	string					true		"group name"
// @Param	uid				path 	string					true		"user id"
// @Param	body			body 	usergroup.GroupUserAdd		true		"to add user to group"
// @Param	token			header	string					true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:groupname/user/:uid [put]
func (p *UserGroupController) ModifyUser() {
	groupname := p.GetString(":groupname")
	userid := p.GetString(":uid")
	p.NeedGroupAdmin(groupname, "Only group admin or superadmin can modify group user")

	mgu_info := new(usergroup.GroupUserAdd)
	json.Unmarshal(p.Ctx.Input.RequestBody, mgu_info)

	mgu := new(usergroup.GroupUser)
	if err := mgu.GetByID(userid, groupname); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	if mgu.Role = role.GetRoleByRolename(mgu_info.Rolename); mgu.Role == nil {
		msg := models.GenerateErrorMsg(500, "Group Role name error")
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	if err := mgu.ModifyInGroup(); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	p.LogMod(4, " 更新 用户[", mgu.User.Username, "]在用户组[", mgu.Group.Name, "]角色成功")
	p.Data["json"] = models.GenerateResponseMsg("Modify success")
	p.ServeJSON()
}

// @Title Delete Group User
// @Description delete user of a group
// @Param	groupname		path 	string			true		"group name"
// @Param	uid				path 	string			true		"user id"
// @Param	token			header	string			true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:groupname/user/:uid [delete]
func (p *UserGroupController) DeleteUser() {
	groupname := p.GetString(":groupname")
	userid := p.GetString(":uid")
	p.NeedGroupAdmin(groupname, "Only group admin or superadmin can delete group user")
	dgu := new(usergroup.GroupUser)

	if err := dgu.GetByID(userid, groupname); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}
	if err := dgu.DeleteFromGroup(); err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		p.Ctx.ResponseWriter.WriteHeader(500)
		p.Data["json"] = msg
		p.ServeJSON()
		return
	}

	p.LogDel(4, "从用户组[", dgu.Group.Name, "]移除用户[", dgu.User.Username, "]成功")

	p.Data["json"] = models.GenerateResponseMsg("Delete success")
	p.ServeJSON()
}
