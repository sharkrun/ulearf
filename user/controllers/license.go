package controllers

import (
	"ufleet/user/license"
	"ufleet/user/models"
)

// Operations about License
type LicenseController struct {
	baseController
}

// @Title Get License info
// @Description get License info
// @Success 200 {object} []role.Role
// @Failure 500 {object} models.ErrorMsg
// @router / [get]
func (s *LicenseController) Get() {
	//s.NeedSuperAdmin("")

	info, err := license.GetLicenseInfo()
	if err != nil {
		s.Ctx.ResponseWriter.WriteHeader(404)
		s.Data["json"] = models.GenerateErrorMsg(404, err.Error())
		s.ServeJSON()
		return
	}

	s.Data["json"] = info
	s.ServeJSON()
}

// @Title Set License
// @Description Set License
// @Param	token			header	string				true		"The login token"
// @Param	body            body 	string				true		"license"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router / [post]
func (s *LicenseController) Set() {
	s.NeedSuperAdmin("")

	certificate := string(s.Ctx.Input.RequestBody)
	if certificate == "" {
		s.LogMod(2, "更新license失败， 证书无效")
		msg := models.GenerateErrorMsg(406, "invalid certificate")
		s.Ctx.ResponseWriter.WriteHeader(406)
		s.Data["json"] = msg
		s.ServeJSON()
		return
	}

	err := license.UpdateLicenseInfo(certificate)
	if err != nil {
		s.LogMod(2, "更新license失败, [", err.Error(), "]")
		s.Ctx.ResponseWriter.WriteHeader(406)
		s.Data["json"] = models.GenerateErrorMsg(406, err.Error())
		s.ServeJSON()
		return
	}

	s.Data["json"] = models.GenerateResponseMsg("update license success")
	s.ServeJSON()

}
