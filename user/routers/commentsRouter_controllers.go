package routers

import (
	"github.com/astaxie/beego"
)

func init() {

	beego.GlobalControllerRouter["ufleet/user/controllers:AbilityController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AbilityController"],
		beego.ControllerComments{
			Method:           "Get",
			Router:           `/`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AbilityController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AbilityController"],
		beego.ControllerComments{
			Method:           "GetInit",
			Router:           `/init`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AbilityController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AbilityController"],
		beego.ControllerComments{
			Method:           "GetAllAbilities",
			Router:           `/all`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AbilityController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AbilityController"],
		beego.ControllerComments{
			Method:           "GetAllRoleAbilities",
			Router:           `/role`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"],
		beego.ControllerComments{
			Method:           "AuthConfigModify",
			Router:           `/`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"],
		beego.ControllerComments{
			Method:           "AuthConfigGet",
			Router:           `/`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"],
		beego.ControllerComments{
			Method:           "LdapConfigGet",
			Router:           `/ldap`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"],
		beego.ControllerComments{
			Method:           "LdapConfigModify",
			Router:           `/ldap`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"],
		beego.ControllerComments{
			Method:           "LdapVerify",
			Router:           `/ldap/verify`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"],
		beego.ControllerComments{
			Method:           "LdapUserGet",
			Router:           `/ldap/user`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:AuthController"],
		beego.ControllerComments{
			Method:           "ImportLdapUser",
			Router:           `/ldap/user`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "AddPublicRegistry",
			Router:           `/public`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "UpdatePublicRegistry",
			Router:           `/public/:id`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "GetPublicRegistry",
			Router:           `/public`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "DeletePublicRegistry",
			Router:           `/public/:id`,
			AllowHTTPMethods: []string{"delete"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "AddGroupRegistry",
			Router:           `/group/:groupname`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "UpdateGroupRegistry",
			Router:           `/group/:groupname/:id`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "GetGroupRegistry",
			Router:           `/group/:groupname`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "DeleteGroupRegistry",
			Router:           `/group/:groupname/:id`,
			AllowHTTPMethods: []string{"delete"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "GetRegistry",
			Router:           `/all`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RegistryController"],
		beego.ControllerComments{
			Method:           "Total",
			Router:           `/total/:groupname`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"],
		beego.ControllerComments{
			Method:           "Post",
			Router:           `/add`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"],
		beego.ControllerComments{
			Method:           "GetRepository",
			Router:           `/`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"],
		beego.ControllerComments{
			Method:           "GetAllRepository",
			Router:           `/all`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"],
		beego.ControllerComments{
			Method:           "GetUserRepository",
			Router:           `/user/:username`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"],
		beego.ControllerComments{
			Method:           "Get",
			Router:           `/:id`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"],
		beego.ControllerComments{
			Method:           "Put",
			Router:           `/:id`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RepositoryController"],
		beego.ControllerComments{
			Method:           "Delete",
			Router:           `/:id`,
			AllowHTTPMethods: []string{"delete"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:RoleController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:RoleController"],
		beego.ControllerComments{
			Method:           "Get",
			Router:           `/`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Post",
			Router:           `/`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "GetAll",
			Router:           `/`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "GetAdminUsers",
			Router:           `/admin`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Get",
			Router:           `/:id`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "GetUserWithGroup",
			Router:           `/withgroup/:id`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "GetAllUserWithGroup",
			Router:           `/withgroup`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "GetGroupRole",
			Router:           `/grouprole`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "GetUsers",
			Router:           `/groupadmin`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Version",
			Router:           `/version`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Put",
			Router:           `/:id`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "ModifyPassword",
			Router:           `/:id/password`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "ModifyProfile",
			Router:           `/:id/profile`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Delete",
			Router:           `/:id`,
			AllowHTTPMethods: []string{"delete"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Deactive",
			Router:           `/deactive/:id`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Active",
			Router:           `/active/:id`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Login",
			Router:           `/login`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Logout",
			Router:           `/logout`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Verify",
			Router:           `/verify/:token`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "VerifyBasicAuth",
			Router:           `/verify/basic/:basicauth`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "SendVerifyCode",
			Router:           `/verifycode/:username`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "ResetPassword",
			Router:           `/reset`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserController"],
		beego.ControllerComments{
			Method:           "Unlock",
			Router:           `/unlock/:id`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "GetAll",
			Router:           `/`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "GetMyGroup",
			Router:           `/my`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "Post",
			Router:           `/`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "Put",
			Router:           `/:groupname`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "Get",
			Router:           `/:groupname`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "Delete",
			Router:           `/:groupname`,
			AllowHTTPMethods: []string{"delete"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "AddUser",
			Router:           `/:groupname/user`,
			AllowHTTPMethods: []string{"post"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "GetAllUser",
			Router:           `/allusers/:groupname`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "GetUser",
			Router:           `/:groupname/user/:uid`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "GetGroup",
			Router:           `/user/:uid`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "ModifyUser",
			Router:           `/:groupname/user/:uid`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:UserGroupController"],
		beego.ControllerComments{
			Method:           "DeleteUser",
			Router:           `/:groupname/user/:uid`,
			AllowHTTPMethods: []string{"delete"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:LicenseController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:LicenseController"],
		beego.ControllerComments{
			Method:           "Get",
			Router:           `/`,
			AllowHTTPMethods: []string{"get"},
			Params:           nil})

	beego.GlobalControllerRouter["ufleet/user/controllers:LicenseController"] = append(beego.GlobalControllerRouter["ufleet/user/controllers:LicenseController"],
		beego.ControllerComments{
			Method:           "Set",
			Router:           `/`,
			AllowHTTPMethods: []string{"put"},
			Params:           nil})

}
