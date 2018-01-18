package controllers

import (
	"encoding/json"

	"ufleet/user/auth"
	"ufleet/user/license"
	"ufleet/user/models"
	"ufleet/user/role"
	"ufleet/user/user"
	"ufleet/user/usergroup"
	"ufleet/user/util/logs"

	"fmt"
	"github.com/astaxie/beego"
)

// Operations about Users
type UserController struct {
	baseController
}

// Post create new user and add user to groups
// @Title Create User
// @Description create users and add to group
// @Param	body	body 	user.UserWithGroup	true  "body for user content"
// @Param	token	header	string		        true  "The login token"
// @Success 200 {string} user.User.Id
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router / [post]
func (u *UserController) Post() {
	u.NeedAdmin("Higher than admin is allowed to add new user")

	newUserWithGroup := user.UserWithGroup{}
	json.Unmarshal(u.Ctx.Input.RequestBody, &newUserWithGroup)
	newUser := newUserWithGroup.User

	if u.User.IsAdmin() || role.IsValidRole(newUser.Role) == false {
		newUser.Role = role.ROLE_GROUP_USER
	}

	if len(newUserWithGroup.Group) == 0 {
		u.LogAdd(2, "创建用户[", newUser.Username, "]失败，没有指定用户组")
		u.Ctx.ResponseWriter.WriteHeader(406)
		u.Data["json"] = models.GenerateErrorMsg(406, "No user group specified")
		u.ServeJSON()
		return
	}

	groupMap := make(map[string]*usergroup.UserGroup)
	for _, group := range newUserWithGroup.Group {
		userGroup := usergroup.UserGroup{}
		err := userGroup.Get(group)
		if err != nil {
			u.LogAdd(2, "创建用户[", newUser.Username, "]失败，获取用户组[", group, "]信息报错[", err.Error(), "]")
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = models.GenerateErrorMsg(500, err.Error())
			u.ServeJSON()
			return
		}
		groupMap[group] = &userGroup
	}

	_, err := user.AddNewUser(&newUser, auth.AUTH_TYPE_LOCAL)
	if err != nil {
		u.LogAdd(2, "创建用户[", newUser.Username, "]失败，[", err.Error(), "]")
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		u.ServeJSON()
		return
	}

	for _, group := range newUserWithGroup.Group {
		newGroupUser := usergroup.GroupUser{}
		newGroupUser.User = &newUser
		if newUser.IsAdmin() {
			newGroupUser.Role = role.GetRoleByRolename(role.ROLE_GROUP_ADMIN)
		} else {
			newGroupUser.Role = role.GetRoleByRolename(role.ROLE_GROUP_USER)
		}

		userGroup, ok := groupMap[group]
		if ok {
			newGroupUser.Group = userGroup
			newGroupUser.AddToGroup()
		} else {
			logs.Error("group[", group, "]info not exist.")
		}
	}

	u.LogAdd(4, "创建用户[", newUser.Username, "]成功")
	u.Data["json"] = newUser.ExportToShow()
	u.ServeJSON()
}

// @Title GetAll
// @Description get all users
// @Param	token	header	string	true	"The login token"
// @Success 200 {object} []user.ShowUser
// @Failure 500 Internal Server Error
// @router / [get]
func (u *UserController) GetAll() {
	u.NeedLogin("")
	loginuser := u.User
	if loginuser.HasAdminPower() {
		users := user.GetAllShowUsers()
		u.Data["json"] = users
	} else {
		users := make([]*user.ShowUser, 0)
		users = append(users, loginuser.ExportToShow())
		u.Data["json"] = users
	}
	u.ServeJSON()
}

// @Title GetAdminUsers
// @Description get all cluster admin users
// @Param	token	header	string	true	"The login token"
// @Success 200 {object} []user.ShowUser
// @Failure 500 Internal Server Error
// @router / [get]
func (u *UserController) GetAdminUsers() {
	u.NeedLogin("")
	loginuser := u.User
	if loginuser.HasAdminPower() {
		users := user.GetAdminUsers()
		u.Data["json"] = users
	} else {
		users := make([]*user.ShowUser, 0)
		u.Data["json"] = users
	}
	u.ServeJSON()
}

// @Title Get
// @Description get user by uid
// @Param	id		path 	string	true		"The key for staticblock"
// @Param	token	header	string	true		"The login token"
// @Success 200 {object} user.ShowUser
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:id [get]
func (u *UserController) Get() {
	u.NeedLogin("")
	loginuser := u.User
	uid := u.GetString(":id")
	if loginuser.HasAdminPower() == false && loginuser.ID != uid {
		msg := models.GenerateErrorMsg(403, "Only can get yourself user info")
		u.Ctx.ResponseWriter.WriteHeader(403)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	var pu = new(user.User)
	if uid != "" {
		err := pu.GetByID(uid)
		if err != nil {
			msg := models.GenerateErrorMsg(500, err.Error())
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = msg
		} else {
			u.Data["json"] = pu.ExportToShow()
		}
	}
	u.ServeJSON()
}

// GetUserWithGroup return a user with group field
// @Title GetUserWithGroup
// @Description get user data with group field by uid
// @Param	id		path 	string	true		"user ID"
// @Param	token	header	string	true		"login Token"
// @Success 200 {object} user.UserWithGroup
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /withgroup/:id [get]
func (u *UserController) GetUserWithGroup() {
	u.NeedLogin("")
	loginUser := u.User
	uid := u.GetString(":id")
	if !loginUser.HasAdminPower() && loginUser.ID != uid {
		errMessage := models.GenerateErrorMsg(403, "Only can get yourself user info")
		u.Ctx.ResponseWriter.WriteHeader(403)
		u.Data["json"] = errMessage
		u.ServeJSON()
		return
	}

	var pu = new(user.User)
	if uid != "" {
		err := pu.GetByID(uid)
		u.Data["json"], err = pu.GetUserWithGroup(uid)
		if err != nil {
			errMessage := models.GenerateErrorMsg(500, err.Error())
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = errMessage
		}
	}
	u.ServeJSON()
}

// GetAllUserWithGroup return all users list with group field
// @Title GetAllUserWithGroup
// @Description get all users data with group field
// @Param	token	header	string	true		"login Token"
// @Success 200 {object} []user.UserWithGroup
// @Failure 500 {object} models.ErrorMsg
// @router /withgroup [get]
func (u *UserController) GetAllUserWithGroup() {
	u.NeedLogin("")
	loginUser := u.User
	if loginUser.HasAdminPower() {
		users, err := u.User.GetAllUserWithGroup()
		if err != nil {
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = err
			u.ServeJSON()
			return
		}
		u.Data["json"] = users
	} else {
		users := []user.UserWithGroup{}
		userWithGroup, err := loginUser.GetUserWithGroup(loginUser.ID)
		if err != nil {
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = err
			u.ServeJSON()
			return
		}
		users = append(users, userWithGroup)
		u.Data["json"] = users
	}
	u.ServeJSON()
}

// @Title Update
// @Description update the user
// @Param	id		path 	string				true	"The uid you want to update"
// @Param	body	body 	user.UserWithGroup	true	"body for user content"
// @Param	token	header	string				true	"The login token"
// @Success 200 {object} user.User
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:id [put]
func (u *UserController) Put() {
	u.NeedAdmin("")
	loginUser := u.User
	uid := u.GetString(":id")

	if uid == "" {
		u.LogMod(2, "修改用户[", uid, "]信息失败，[ID 无效]")
		msg := models.GenerateErrorMsg(404, "User id not found")
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}
	updateUser := user.User{}
	err := updateUser.GetByID(uid)
	if err != nil {
		u.LogMod(2, "修改用户[", uid, "]信息失败，[", err.Error(), "]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	userWithGroup := user.UserWithGroup{}
	json.Unmarshal(u.Ctx.Input.RequestBody, &userWithGroup)

	//if len(userWithGroup.Group) == 0 {
	//	u.LogAdd(2, "修改用户[", updateUser.Username, "]失败，没有指定用户组")
	//	u.Ctx.ResponseWriter.WriteHeader(406)
	//	u.Data["json"] = models.GenerateErrorMsg(406, "No user group specified")
	//	u.ServeJSON()
	//	return
	//}

	groupMap := make(map[string]*usergroup.UserGroup)
	for _, group := range userWithGroup.Group {
		userGroup := usergroup.UserGroup{}
		err := userGroup.Get(group)
		if err != nil {
			u.LogAdd(2, "修改用户[", updateUser.Username, "]失败，获取用户组[", group, "]信息报错[", err.Error(), "]")
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = models.GenerateErrorMsg(500, err.Error())
			u.ServeJSON()
			return
		}
		groupMap[group] = &userGroup
	}

	// Only super administrators can modify user roles
	if !loginUser.IsSuperAdmin() {
		userWithGroup.User.Role = updateUser.Role
	}

	if err := updateUser.Update(&userWithGroup.User); err != nil {
		u.LogMod(2, "修改用户[", updateUser.Username, "]信息失败，[更新用户信息失败]")
		msg := models.GenerateErrorMsg(500, "modify fail")
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	// delete all user in groups
	oldGroup, err := updateUser.GetUserWithGroup(updateUser.ID)
	if err != nil {
		u.LogMod(2, "修改用户[", updateUser.Username, "]信息失败，[更新用户组信息失败]")
		msg := models.GenerateErrorMsg(500, "update group error!")
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	var del_groups []string
	var add_groups []string

	for _, old_group := range oldGroup.Group {
		match := 0
		for _, new_group := range userWithGroup.Group {
			if old_group == new_group {
				match = 1
			}
		}
		if match == 0 {
			del_groups = append(del_groups, old_group)
		}
	}

	for _, new_group := range userWithGroup.Group {
		match := 0
		for _, old_group := range oldGroup.Group {
			if old_group == new_group {
				match = 1
			}
		}
		if match == 0 {
			add_groups = append(add_groups, new_group)
		}
	}

	for _, group := range del_groups {
		dgu := new(usergroup.GroupUser)
		if err := dgu.GetByID(updateUser.ID, group); err != nil {
			msg := models.GenerateErrorMsg(500, err.Error())
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = msg
			u.ServeJSON()
			return
		}
		if err := dgu.DeleteFromGroup(); err != nil {
			msg := models.GenerateErrorMsg(500, err.Error())
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = msg
			u.ServeJSON()
			return
		}
	}
	// add user to all post groups
	for _, group := range add_groups {
		newGroupUser := usergroup.GroupUser{}
		newGroupUser.User = &updateUser
		if updateUser.IsAdmin() {
			newGroupUser.Role = role.GetRoleByRolename(role.ROLE_GROUP_ADMIN)
		} else {
			newGroupUser.Role = role.GetRoleByRolename(role.ROLE_GROUP_USER)
		}

		userGroup, ok := groupMap[group]
		if ok {
			newGroupUser.Group = userGroup
			newGroupUser.AddToGroup()
		} else {
			logs.Error("group[", group, "]info not exist.")
		}
	}
	u.LogMod(4, "修改用户[", updateUser.Username, "]信息成功")
	u.Data["json"] = updateUser.ExportToShow()
	u.ServeJSON()
}

// @Title UpdatePassword
// @Description update the user's password
// @Param	id		path 	string		true		"The uid you want to update"
// @Param	body	body 	user.PasswordModify	true		"body for user to modify password"
// @Param	token	header	string		true		"The login token"
// @Success 200 {object} user.User
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:id/password [put]
func (u *UserController) ModifyPassword() {
	u.NeedLogin("")
	loginuser := u.User

	uid := u.GetString(":id")
	if loginuser.HasAdminPower() == false && loginuser.ID != uid {
		u.LogMod(2, "修改用户[", uid, "]密码失败,[权限不足]")
		msg := models.GenerateErrorMsg(403, "Only can modify yourself user info")
		u.Ctx.ResponseWriter.WriteHeader(403)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	if uid == "" {
		u.LogMod(2, "修改用户[", uid, "]密码失败,[ID 无效]")
		msg := models.GenerateErrorMsg(404, "User id not found")
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	var pu = new(user.User)
	if err := pu.GetByID(uid); err != nil {
		u.LogMod(2, "修改用户[", uid, "]密码失败,[用户不存在]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	if pu.HasAdminPower() && !loginuser.IsSuperAdmin() && loginuser.ID != uid {
		u.LogMod(2, "修改用户[", pu.Username, "]密码失败,[权限不足]")
		msg := models.GenerateErrorMsg(403, "Only super admin can not modify admin power user password")
		u.Ctx.ResponseWriter.WriteHeader(403)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	var mpassword = new(user.PasswordModify)
	json.Unmarshal(u.Ctx.Input.RequestBody, mpassword)

	if err := pu.UpdatePassword(mpassword); err != nil {
		u.LogMod(2, "修改用户[", pu.Username, "]密码失败,[", err.Error(), "]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	u.LogMod(4, "修改用户[", pu.Username, "]密码成功")

	u.Data["json"] = pu.ExportToShow()
	u.ServeJSON()
}

// @Title UpdateProfile
// @Description update the user's profile
// @Param	id		path 	string		true		"The uid you want to update"
// @Param	body	body 	user.PasswordModify	true		"body for user to modify profile"
// @Param	token	header	string		true		"The login token"
// @Success 200 {object} user.User
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:id/profile [put]
func (u *UserController) ModifyProfile() {
	u.NeedLogin("")
	loginuser := u.User

	uid := u.GetString(":id")
	if loginuser.HasAdminPower() == false && loginuser.ID != uid {
		u.LogMod(2, "修改用户[", uid, "]基本信息失败,[权限不足]")
		msg := models.GenerateErrorMsg(403, "Only can modify yourself user info")
		u.Ctx.ResponseWriter.WriteHeader(403)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	if uid == "" {
		u.LogMod(2, "修改用户[", uid, "]基本信息失败,[ID无效]")
		msg := models.GenerateErrorMsg(404, "User id not found")
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	var pu = new(user.User)
	if err := pu.GetByID(uid); err != nil {
		u.LogMod(2, "修改用户[", uid, "]基本信息失败,[用户不存在]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	if pu.HasAdminPower() && !loginuser.IsSuperAdmin() && loginuser.ID != uid {
		u.LogMod(2, "修改用户[", pu.Username, "]基本信息失败,[权限不足]")
		msg := models.GenerateErrorMsg(403, "Only super admin can not modify admin power user password")
		u.Ctx.ResponseWriter.WriteHeader(403)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	var profile = new(user.Profile)
	json.Unmarshal(u.Ctx.Input.RequestBody, profile)

	if err := pu.UpdateProfile(profile); err != nil {
		u.LogMod(2, "修改用户[", pu.Username, "]基本信息失败,[", err.Error(), "]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	u.LogMod(4, "修改用户[", pu.Username, "]基本信息成功")
	u.Data["json"] = pu.ExportToShow()
	u.ServeJSON()
}

// @Title Delete
// @Description delete the user
// @Param	id		path 	string		true		"The uid you want to delete"
// @Param	token	header	string		true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:id [delete]
func (u *UserController) Delete() {
	u.NeedAdmin("You need administrator privileges to delete users")

	uid := u.GetString(":id")
	var pu = new(user.User)
	var ppu = new(usergroup.GroupUser)

	if err := pu.GetByID(uid); err != nil {
		u.LogDel(2, "删除用户[", uid, "]失败，[用户不存在]")
		msg := models.GenerateErrorMsg(404, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	if u.User.IsAdmin() && pu.HasAdminPower() {
		u.LogDel(2, "删除用户[", pu.Username, "]失败，[需要superadmin权限]")
		msg := models.GenerateErrorMsg(405, "Super administrator rights required.")
		u.Ctx.ResponseWriter.WriteHeader(405)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	ppu.User = pu

	if err := ppu.CleanInAllGroup(); err != nil {
		u.LogDel(2, "删除用户[", pu.Username, "]失败，[移除用户组信息失败]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	if err := pu.Delete(); err != nil {
		u.LogDel(2, "删除用户[", pu.Username, "]失败，[删除失败]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	if err := pu.Clean(); err != nil {
		u.LogDel(2, "删除用户[", pu.Username, "]失败，[清除用户信息失败]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}
	u.LogDel(4, "删除用户[", pu.Username, "]成功")

	u.Data["json"] = models.GenerateResponseMsg("delete success")
	u.ServeJSON()
}

// @Title Deactive
// @Description deactive the user
// @Param	id		path 	string	true		"The uid you want to deactive"
// @Param	token	header	string	true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /deactive/:id [get]
func (u *UserController) Deactive() {
	u.NeedAdmin("Higher than admin can deactive user")

	uid := u.GetString(":id")
	var pu = new(user.User)

	err := pu.GetByID(uid)
	if err != nil {
		u.LogMod(2, "去激活用户[", uid, "]失败,[用户不存在]")
		msg := models.GenerateErrorMsg(404, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	err = pu.Deactive()
	if err != nil {
		u.LogMod(2, "去激活用户[", uid, "]失败,[去激活失败]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}
	u.LogMod(4, "去激活用户[", pu.Username, "]成功")
	u.Data["json"] = models.GenerateResponseMsg("deactive success")
	u.ServeJSON()
}

// @Title Active
// @Description Active the user
// @Param	id		path 	string	true		"The uid you want to active"
// @Param	token	header	string	true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /active/:id [get]
func (u *UserController) Active() {
	u.NeedAdmin("Higher than admin can active user")

	uid := u.GetString(":id")
	var pu = new(user.User)

	err := pu.GetByID(uid)
	if err != nil {
		u.LogMod(2, "激活用户[", uid, "]失败,[用户不存在]")
		msg := models.GenerateErrorMsg(404, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	err = pu.Active()
	if err != nil {
		u.LogMod(2, "激活用户[", pu.Username, "]失败,[激活失败]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	u.LogMod(4, "激活用户[", pu.Username, "]成功")

	u.Data["json"] = models.GenerateResponseMsg("active success")
	u.ServeJSON()
}

// @Title Unlock user
// @Description Active the user
// @Param	id		path 	string	true		"The uid you want to unlock"
// @Param	token	header	string	true		"The login token"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /unlock/:id [get]
func (u *UserController) Unlock() {
	u.NeedAdmin("Higher than admin can unlock user")

	uid := u.GetString(":id")
	var pu = new(user.User)

	err := pu.GetByID(uid)
	if err != nil {
		u.LogMod(2, "解锁用户[", uid, "]失败,[用户不存在]")
		msg := models.GenerateErrorMsg(404, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	err = pu.Unlock()
	if err != nil {
		u.LogMod(2, "解锁用户[", pu.Username, "]失败,[解锁失败]")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	u.LogMod(4, "解锁用户[", pu.Username, "]成功")

	u.Data["json"] = models.GenerateResponseMsg("unlock success")
	u.ServeJSON()
}

// @Title Login
// @Description Logs user into the system
// @Param	body		body 	user.LoginInfo	true		"login info of user"
// @Success 200 {object} user.Token
// @Failure 404 {object} models.ErrorMsg
// @router /login [post]
func (u *UserController) Login() {
	var ul = new(user.LoginInfo)
	json.Unmarshal(u.Ctx.Input.RequestBody, ul)
	if token, berr := user.Login(ul.Username, ul.Password); berr.Errs == nil {
		u.Data["json"] = token
		logs.Logetcd(4, ul.Username, "登录", ul.Username, "登录成功")
		logs.Info(fmt.Sprintf("user [%s] 登录成功，token %s", ul.Username, token.Token))
	} else {
		msg := models.GenerateErrorMsg(404, berr.StatusDtl.Desc)
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		logs.Logetcd(3, ul.Username, "登录", ul.Username, "登录失败")
	}
	u.ServeJSON()
}

// @Title logout
// @Description Logs out current logged in user session
// @Param	body	body 	user.LogoutToken	true		"The token of user you want to logout"
// @Param	token	header	string	true		"The login token"
// @Success 200 {string} token
// @Failure 500 {object} models.ErrorMsg
// @router /logout [post]
func (u *UserController) Logout() {
	u.NeedLogin("")

	token, _ := u.Ctx.Request.Header["Token"]

	ret, err := user.Logout(token[0])
	if ret != true {
		logs.Logetcd(3, u.User.Username, "登出", u.User.Username, "登出失败")
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
	} else {
		logs.Logetcd(4, u.User.Username, "登出", u.User.Username, "登出成功")
		msg := models.GenerateResponseMsg("logout success")
		u.Data["json"] = msg
		logs.Info(fmt.Sprintf("user [%s] 登出成功，token %s", u.User.Username, token[0]))
	}

	u.ServeJSON()
}

// @Title verify token
// @Description verify user token to check login status
// @Param	token		path 	string	true		"token of user"
// @Success 200 {object} user.User
// @Failure 401 {object} models.ErrorMsg
// @router /verify/:token [get]
func (u *UserController) Verify() {
	token := u.GetString(":token")
	if token != "" {
		pu, err := user.VerifyToken(token)
		if err != nil {
			msg := models.GenerateErrorMsg(401, err.Error())
			u.Ctx.ResponseWriter.WriteHeader(401)
			u.Data["json"] = msg
		} else {
			// if exist a valid license
			linfo, _ := license.GetLicenseInfo()
			pu.Licensed = linfo != nil
			u.Data["json"] = pu
		}
	}
	u.ServeJSON()
}

// @Title verify basic auth
// @Description verify user basic auth to check login status
// @Param	basicauth		path 	string	true		"basic auth info of user"
// @Success 200 {object} user.User
// @Failure 401 {object} models.ErrorMsg
// @router /verify/basic/:basicauth [get]
func (u *UserController) VerifyBasicAuth() {
	basicauth := u.GetString(":basicauth")
	if len(basicauth) > 0 {
		pu, err := user.VerifyBasicAuth(basicauth)
		if err != nil {
			msg := models.GenerateErrorMsg(401, err.Error())
			u.Ctx.ResponseWriter.WriteHeader(401)
			u.Data["json"] = msg
		} else {
			u.Data["json"] = pu
		}
	}
	u.ServeJSON()
}

// GetGroupRole return usergroup and role data
// 2017-04-25 edit by robin, zhiqiang.li@youruncloud.com
// @Title GetGroupRole
// @Description get user group and role by token
// @Param    token    header    string    true    "The login token"
// @Success 200 {object} []user.UserGroupRole
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /grouprole [get]
func (u *UserController) GetGroupRole() {
	u.NeedLogin("")
	groupRoleList := []user.UserGroupRole{}
	groupList := u.User.GetUserGroup()
	for _, group := range groupList {
		groupRole := user.UserGroupRole{}
		groupUser := usergroup.GroupUser{}
		err := groupUser.GetByName(u.User.Username, group)
		if err != nil {
			continue
		}
		groupRole.Group = group
		if u.User.IsAdmin() {
			groupRole.Role = role.ROLE_GROUP_ADMIN
		} else {
			groupRole.Role = groupUser.Role.Role
		}

		groupRoleList = append(groupRoleList, groupRole)
	}
	u.Data["json"] = groupRoleList
	u.ServeJSON()
}

// GetUsers return all user to group admin or admin
// 2017-04-25 edit by robin, zhiqiang.li@youruncloud.com
// @Title GetUsers
// @Description get all users
// @Param	token	header	string	true	"The login token"
// @Success 200 {object} []user.ShowUser
// @Failure 500 Internal Server Error
// @router /groupadmin [get]
func (u *UserController) GetUsers() {
	u.NeedLogin("")
	loginUser := u.User
	if loginUser.HasAdminPower() {
		users := user.GetAllShowUsers()
		u.Data["json"] = users
	} else {
		users := make([]*user.ShowUser, 0)
		users = append(users, loginUser.ExportToShow())
		u.Data["json"] = users
	}
	groupList := u.User.GetUserGroup()
	roleList := []string{}
	for _, group := range groupList {
		groupUser := usergroup.GroupUser{}
		err := groupUser.GetByName(u.User.Username, group)
		if err != nil {
			continue
		}
		roleList = append(roleList, groupUser.Role.Role)
	}
	for _, roles := range roleList {
		if roles == "group_admin" {
			users := user.GetAllShowUsers()
			u.Data["json"] = users
		}
	}
	u.ServeJSON()
}

// Version return user module version
// 2017-04-25 edit by robin, zhiqiang.li@youruncloud.com
// @Title Version
// @Description get user module version
// @Param	token	header	string	true	"The login token"
// @Success 200 string
// @Failure 500 Internal Server Error
// @router /version [get]
func (u *UserController) Version() {
	u.NeedLogin("")
	v := map[string]string{}
	v["version"] = beego.AppConfig.String("Version")
	u.Data["json"] = v
	u.ServeJSON()
}

// SendVerifyCode
// @Title Send verify code for reset password
// @Description Send verify code for reset password
// @Param	username	header	string	true	"The username of the user"
// @Success 200 string
// @Failure 500 Internal Server Error
// @router /version [get]
func (u *UserController) SendVerifyCode() {
	username := u.GetString(":username")
	if len(username) == 0 {
		logs.Logetcd(2, "system", "发送验证码", "发送验证码失败,[用户名非法]")
		logs.Error("SendVerifyCode fail, as[username invalid]")
		msg := models.GenerateErrorMsg(404, "username invalid")
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	authtype := auth.GetAuthType()
	if authtype != auth.AUTH_TYPE_LOCAL {
		logs.Logetcd(2, username, "发送验证码", "给[", username, "]发送验证码失败,[LDAP验证模式不支持通过验证码重置密码]")
		msg := models.GenerateErrorMsg(405, "Please reset password by ldap")
		u.Ctx.ResponseWriter.WriteHeader(405)
		u.Data["json"] = msg
		return
	}

	err := user.SendRandomStr(username)
	if err != nil {
		logs.Logetcd(2, username, "发送验证码", "给[", username, "]发送验证码失败,[", err.Error(), "]")
		msg := models.GenerateErrorMsg(405, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(405)
		u.Data["json"] = msg
		return
	}

	u.Data["json"] = models.GenerateResponseMsg("send verify code success")
	u.ServeJSON()
}

// ResetPassword
// @Title reset user password
// @Description reset user password
// @Success 200 string
// @Failure 500 Internal Server Error
// @router /version [post]
func (u *UserController) ResetPassword() {
	var info = new(user.ResetInfo)
	err := json.Unmarshal(u.Ctx.Input.RequestBody, info)
	if err != nil {
		logs.Error("ResetPassword Unmarshal reset info fail.")
		msg := models.GenerateErrorMsg(405, "user info invalid")
		u.Ctx.ResponseWriter.WriteHeader(405)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	if err := user.ResetPassword(info.Username, info.Password, info.Veryfycode); err == nil {
		logs.Logetcd(4, info.Username, "重置密码", info.Username, "重置密码成功")
		msg := models.GenerateResponseMsg("reset success")
		u.Data["json"] = msg
	} else {
		msg := models.GenerateErrorMsg(404, "Reset password fail")
		u.Ctx.ResponseWriter.WriteHeader(404)
		u.Data["json"] = msg
		logs.Logetcd(3, info.Username, "重置密码", info.Username, "重置密码失败")
	}
	u.ServeJSON()
}
