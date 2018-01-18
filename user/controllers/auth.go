package controllers

import (
	"encoding/json"
	//"errors"
	//"log"

	"ufleet/user/auth"
	"ufleet/user/models"
	"ufleet/user/role"
	"ufleet/user/user"
	"ufleet/user/usergroup"
	//"ufleet/user/user"
	//log "ufleet/user/util/logs"
)

//AuthController Operations about Auth
type AuthController struct {
	baseController
}

// @Title Modify Auth Config
// @Description modify auth config
// @Param	body	body 	auth.SystemAuthConfig	true		"to adjust system auth config"
// @Param	token	header	string					true		"The login token"
// @Success 200 {string} auth.SystemAuthConfig
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router / [post]
func (u *AuthController) AuthConfigModify() {
	u.NeedSuperAdmin("Only superadmin can modify auth config")

	var authdata auth.SystemAuthConfig
	json.Unmarshal(u.Ctx.Input.RequestBody, &authdata)
	switch authdata.Type {
	case auth.AUTH_TYPE_LOCAL:
		fallthrough
	case auth.AUTH_TYPE_LDAP:
		auth.SetAuthType(authdata.Type)
		u.Data["json"] = authdata
	default:
		msg := models.GenerateErrorMsg(500, "auth type unkown")
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
	}
	u.ServeJSON()
}

// @Title Get Auth Config
// @Description get auth config
// @Success 200 {object} auth.SystemAuthConfig
// @Failure 500 {object} models.ErrorMsg
// @router / [get]
func (u *AuthController) AuthConfigGet() {
	config := auth.ReloadAuthInfo()
	u.Data["json"] = *config
	u.ServeJSON()
}

// @Title Get LDAP Config
// @Description get ldap config
// @Success 200 {object} auth.SystemLdapConfig
// @Failure 500 {object} models.ErrorMsg
// @router /ldap [get]
func (u *AuthController) LdapConfigGet() {
	config := auth.ReloadLdapConfig()
	u.Data["json"] = config
	u.ServeJSON()
}

// @Title Modify LDAP Config
// @Description modify auth config
// @Param	body		body 	auth.SystemLdapConfig	true		"to adjust ldap config"
// @Param	token	header	string					true		"The login token"
// @Success 200 {object} auth.SystemLdapConfig
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /ldap [post]
func (u *AuthController) LdapConfigModify() {
	u.NeedAdmin("Higher than admin can modify LDAP config")

	var ldapconfig = auth.InitLdapConfig()
	err := json.Unmarshal(u.Ctx.Input.RequestBody, ldapconfig)
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}

	auth.SaveLdapConfig(ldapconfig)
	u.Data["json"] = ldapconfig
	u.ServeJSON()
}

// @Title LDAP Config test
// @Description test ldap verify ability
// @Param	body		body 	auth.LdapVerifyData	true		"login info of user"
// @Success 200 {object} auth.LdapVerifyResult
// @Failure 500 {object} models.ErrorMsg
// @router /ldap/verify [post]
func (u *AuthController) LdapVerify() {
	var verifyaccount auth.LdapVerifyData
	var result auth.LdapVerifyResult
	err := json.Unmarshal(u.Ctx.Input.RequestBody, &verifyaccount)
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}
	_, ok := auth.LdapVerify(verifyaccount.Username, verifyaccount.Password)
	result.Result = ok
	u.Data["json"] = result
	u.ServeJSON()
}

// @Title Get LDAP user
// @Description get ldap user
// @Param	token	header	string					true		"The login token"
// @Success 200 {object} []auth.LdapUser
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /ldap/user [get]
func (u *AuthController) LdapUserGet() {
	u.NeedAdmin("Higher than admin can get LDAP user list")

	ldapUserList, err := auth.LdapListUser()
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}
	for _, lu := range ldapUserList {
		user.LdapUserIsExistInSystem(lu)
	}
	u.Data["json"] = ldapUserList
	u.ServeJSON()
}

// @Title Add LDAP user to system
// @Description add ldap user to system
// @Param	token	header	string			true		"The login token"
// @Param	body	body 	auth.LdapUser	true		"the info of ldap user"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /ldap/users [post]
func (u *AuthController) LdapUserAdd() {
	u.NeedAdmin("Higher than admin can add LDAP user to system")

	addlu := new(auth.LdapUser)
	if err := json.Unmarshal(u.Ctx.Input.RequestBody, addlu); err != nil {
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = err
		u.ServeJSON()
		return
	}
	if len(addlu.Username) == 0 {
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = models.GenerateErrorMsg(500, "No Username provided")
		u.ServeJSON()
		return
	}
	ldapUserList, err := auth.LdapListUser()
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = msg
		u.ServeJSON()
		return
	}
	for _, lu := range ldapUserList {
		if lu.Username == addlu.Username {
			if _, err := user.LdapUserAddToSystem(lu); err != nil {
				msg := models.GenerateErrorMsg(500, err.Error())
				u.Ctx.ResponseWriter.WriteHeader(500)
				u.Data["json"] = msg
				u.ServeJSON()
				return
			}
		}
	}
	u.Data["json"] = models.GenerateResponseMsg("add success")
	u.ServeJSON()
}

// @Title Add LDAP user to system
// @Description add ldap user to system
// @Param	token	header	string			true		"The login token"
// @Param	body	body 	auth.LdapUserData	true		"the info of ldap user and group"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /ldap/user [post]
func (u *AuthController) ImportLdapUser() {
	u.NeedAdmin("Higher than admin can add LDAP user to system")

	userData := new(auth.LdapUserData)
	if err := json.Unmarshal(u.Ctx.Input.RequestBody, userData); err != nil {
		u.Ctx.ResponseWriter.WriteHeader(500)
		u.Data["json"] = err
		u.ServeJSON()
		return
	}

	userList := make([]*auth.LdapUser, 0)
	for _, addlu := range userData.Users {
		if len(addlu.Username) == 0 {
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = models.GenerateErrorMsg(500, "No Username provided")
			u.ServeJSON()
			return
		}
		//验证这个ldap用户是否存在
		lu, ok := auth.LdapGetUser(addlu.Username)
		if !ok {
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = models.GenerateErrorMsg(500, "The ldap user not exist")
			u.ServeJSON()
			return
		}
		userList = append(userList, lu)
	}
	for _, lu := range userList {
		newuser, err := user.LdapUserAddToSystem(lu)
		if err != nil {
			msg := models.GenerateErrorMsg(500, err.Error())
			u.Ctx.ResponseWriter.WriteHeader(500)
			u.Data["json"] = msg
			u.ServeJSON()
			return
		}

		for _, group := range userData.Group {
			newGroupUser := usergroup.GroupUser{}
			newGroupUser.User = newuser
			newGroupUser.Role = role.GetRoleByRolename("group_user")
			userGroup := usergroup.UserGroup{}
			err := userGroup.Get(group)
			if err != nil {
				u.Ctx.ResponseWriter.WriteHeader(500)
				u.Data["json"] = models.GenerateErrorMsg(500, err.Error())
				u.ServeJSON()
				return
			}
			newGroupUser.Group = &userGroup
			newGroupUser.AddToGroup()
		}
	}

	u.Data["json"] = models.GenerateResponseMsg("add success")
	u.ServeJSON()
}
