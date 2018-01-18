// @APIVersion 1.0.0
// @Title ufleet project user module
// @Description ufleet project
// @Contact alfred.huang@youruncloud.com
package routers

import (
	"ufleet/user/controllers"

	"github.com/astaxie/beego"
)

func init() {
	ns := beego.NewNamespace("/v1",
		beego.NSNamespace("/user",
			beego.NSInclude(
				&controllers.UserController{},
			),
		),
		beego.NSNamespace("/auth",
			beego.NSInclude(
				&controllers.AuthController{},
			),
		),
		beego.NSNamespace("/role",
			beego.NSInclude(
				&controllers.RoleController{},
			),
		),
		beego.NSNamespace("/usergroup",
			beego.NSInclude(
				&controllers.UserGroupController{},
			),
		),
		/*
			beego.NSNamespace("/ability",
				beego.NSInclude(
					&controllers.AbilityController{},
				),
			),
		*/
		beego.NSNamespace("/registry",
			beego.NSInclude(
				&controllers.RegistryController{},
			),
		),
		beego.NSNamespace("/repository",
			beego.NSInclude(
				&controllers.RepositoryController{},
			),
		),
		beego.NSNamespace("/license",
			beego.NSInclude(
				&controllers.LicenseController{},
			),
		),
	)
	beego.AddNamespace(ns)
}
