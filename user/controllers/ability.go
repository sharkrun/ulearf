package controllers

import (
	//"encoding/json"
	//"errors"
	//"log"

	//"ufleet/user/auth"
	"ufleet/user/ability"
	"ufleet/user/models"
	//"ufleet/user/projrole"
)

// Operations about Ability
type AbilityController struct {
	baseController
}

// @Title Get User model ability list info
// @Description get ability list
// @Success 200 {object} []ability.Ability
// @Failure 500 {object} models.ErrorMsg
// @router / [get]
func (a *AbilityController) Get() {
	list, err := ability.ReadAbilityListFromFile(ability.GetAbilityFilePath())
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		a.Ctx.ResponseWriter.WriteHeader(500)
		a.Data["json"] = msg
		a.ServeJSON()
		return
	}
	a.Data["json"] = list
	a.ServeJSON()
}

// @Title Get User model ability init list info
// @Description get ability init list
// @Success 200 {object} []ability.RoleAbility
// @Failure 500 {object} models.ErrorMsg
// @router /init [get]
func (a *AbilityController) GetInit() {
	list, err := ability.ReadRoleAbilityListFromFile(ability.GetRoleAbilityFilePath())
	if err != nil {
		msg := models.GenerateErrorMsg(500, err.Error())
		a.Ctx.ResponseWriter.WriteHeader(500)
		a.Data["json"] = msg
		a.ServeJSON()
		return
	}
	a.Data["json"] = list
	a.ServeJSON()
}

//添加一个面向ui的获取全局ability的接口
//返回各个组件的能够提供的ability
//这些ability能够赋值给某些role,role的角色的ability是可以进行更改的

// @Title Get abilities from all module
// @Description get all abilities
// @Success 200 {object} []ability.Ability
// @Failure 500 {object} models.ErrorMsg
// @router /all [get]
func (a *AbilityController) GetAllAbilities() {
	a.Data["json"] = ability.AbilityList
	a.ServeJSON()

}

// @Title Get rool abilities from all module
// @Description get all rool abilities
// @Success 200 {object} []ability.RoleAbility
// @Failure 500 {object} models.ErrorMsg
// @router /role [get]
func (a *AbilityController) GetAllRoleAbilities() {
	a.Data["json"] = ability.RoleAbilityList
	a.ServeJSON()
}
