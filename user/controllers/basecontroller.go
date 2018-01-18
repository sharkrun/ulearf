package controllers

import (

	//"errors"
	//"log"

	"github.com/astaxie/beego"
	"ufleet/user/models"
	"ufleet/user/user"
	"ufleet/user/usergroup"
	"ufleet/user/util/logs"
)

type baseController struct {
	beego.Controller
	User          *user.User
	IsLogin       bool
	LoginCheckMsg string
}

func (b *baseController) Prepare() {
	b.UserLoginCheck()
}

func (b *baseController) UserLoginCheck() {
	token, ok := b.Ctx.Request.Header["Token"]
	if ok {
		u, err := user.VerifyToken(token[0])
		if err == nil {
			b.User = u
			b.IsLogin = true
		} else {
			b.LoginCheckMsg = "Verify token error"
		}
	}
}

func (b *baseController) NeedLogin(errMsg string) {
	if b.IsLogin == false {
		b.Ctx.ResponseWriter.WriteHeader(401)
		if len(errMsg) > 0 {
			b.Data["json"] = models.GenerateErrorMsg(401, b.LoginCheckMsg)
		} else if len(b.LoginCheckMsg) > 0 {
			b.Data["json"] = models.GenerateErrorMsg(401, b.LoginCheckMsg)
		} else {
			b.Data["json"] = models.GenerateErrorMsg(401, "Need login")
		}
		b.ServeJSON()
		b.StopRun()
	}
}

func (b *baseController) NeedSuperAdmin(errMsg string) {
	b.NeedLogin(errMsg)
	if b.User.IsSuperAdmin() == false {
		b.Ctx.ResponseWriter.WriteHeader(403)
		if len(errMsg) > 0 {
			b.Data["json"] = models.GenerateErrorMsg(403, errMsg)
		} else {
			b.Data["json"] = models.GenerateErrorMsg(403, "Need superadmin")
		}
		b.ServeJSON()
		b.StopRun()
	}
}

func (b *baseController) NeedAdmin(errMsg string) {
	b.NeedLogin(errMsg)
	if b.User.IsSuperAdmin() {
		return
	}
	if b.User.IsAdmin() == false {
		b.Ctx.ResponseWriter.WriteHeader(403)
		if len(errMsg) > 0 {
			b.Data["json"] = models.GenerateErrorMsg(403, errMsg)
		} else {
			b.Data["json"] = models.GenerateErrorMsg(403, "Need admin")
		}
		b.ServeJSON()
		b.StopRun()
	}
}

func (b *baseController) NeedGroupAdmin(groupname string, errMsg string) {
	b.NeedLogin("")
	if b.User.HasAdminPower() {
		return
	}

	groupuser := new(usergroup.GroupUser)
	err := groupuser.GetByID(b.User.ID, groupname)
	if err != nil {
		b.Ctx.ResponseWriter.WriteHeader(500)
		b.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		b.ServeJSON()
		b.StopRun()
	}

	if groupuser.Role.IsGroupAdmin() {
		return
	}
	b.Ctx.ResponseWriter.WriteHeader(403)
	if len(errMsg) > 0 {
		b.Data["json"] = models.GenerateErrorMsg(403, errMsg)
	} else {
		b.Data["json"] = models.GenerateErrorMsg(403, "Need group admin")
	}
	b.ServeJSON()
	b.StopRun()
}

func getUserModuleEndpoint() string {
	return "http://127.0.0.1:8881"
}

func (b *baseController) LogAdd(level int, v ...interface{}) {
	operator := "guest"
	if b.IsLogin {
		operator = b.User.Username
	}
	logs.Logetcd(level, operator, "创建", v...)
}

func (b *baseController) LogDel(level int, v ...interface{}) {
	operator := "guest"
	if b.IsLogin {
		operator = b.User.Username
	}
	logs.Logetcd(level, operator, "删除", v...)
}

func (b *baseController) LogMod(level int, v ...interface{}) {
	operator := "guest"
	if b.IsLogin {
		operator = b.User.Username
	}
	logs.Logetcd(level, operator, "修改", v...)
}
func (b *baseController) Logfind(level int, v ...interface{}) {
	operator := "guest"
	if b.IsLogin {
		operator = b.User.Username
	}
	logs.Logetcd(level, operator, "查询", v...)
}
