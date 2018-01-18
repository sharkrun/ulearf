package controllers

import (
	"encoding/json"
	"ufleet/user/models"
	"ufleet/user/registry"
)

// Operations about Registry
type RegistryController struct {
	baseController
}

// @Title Add Public Registry
// @Description add public registry
// @Param	token	header	string				true		"The login token"
// @Param	body	body 	registry.Registry	true		"registry info"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /public [post]
func (c *RegistryController) AddPublicRegistry() {
	c.NeedAdmin("Higher than admin can add public registry")

	var reg = new(registry.Registry)
	err := json.Unmarshal(c.Ctx.Input.RequestBody, reg)
	if err != nil {
		c.LogAdd(2, "创建公有镜像仓库[", reg.Name, "] 失败,[", err.Error(), "]")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}
	err = reg.Add(registry.PUBLIC_REGISTRY)
	if err != nil {
		c.LogAdd(2, "创建公有镜像仓库[", reg.Name, "] 失败,[", err.Error(), "]")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}

	c.LogAdd(4, "创建公有镜像仓库[", reg.Name, "] 成功")
	c.Data["json"] = models.GenerateResponseMsg("Add success")
	c.ServeJSON()
}

// @Title Get public registry
// @Description get public registry
// @Param	token	header	string		true		"The login token"
// @Success 200 {object} []registry.Registry
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /public [get]
func (c *RegistryController) GetPublicRegistry() {
	allreg := registry.GetGroupRegistry(registry.PUBLIC_REGISTRY)
	c.Data["json"] = allreg
	c.ServeJSON()
}

// @Title Delete Public Registry
// @Description delete public registry
// @Param	token		header	string		true		"The login token"
// @Param	address		path 	string		true		"address of registry"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /public/:name [delete]
func (c *RegistryController) DeletePublicRegistry() {
	c.NeedAdmin("Higher than admin can delete public registry")

	var reg = new(registry.Registry)
	reg.ID = c.GetString(":id")
	err := reg.Remove(registry.PUBLIC_REGISTRY)
	if err != nil {
		c.LogDel(2, "删除公有镜像仓库[", reg.ID, "] 失败")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}
	c.LogDel(4, "删除公有镜像仓库[", reg.Name, "] 成功")
	c.Data["json"] = models.GenerateResponseMsg("Delete success")
	c.ServeJSON()
}

// @Title Add Group Registry
// @Description add group registry
// @Param	token			header	string				true		"The login token"
// @Param	groupname		path 	string				true		"group name"
// @Param	body			body 	registry.Registry	true		"registry info"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /group/:groupname [post]
func (c *RegistryController) AddGroupRegistry() {
	groupname := c.GetString(":groupname")
	c.NeedGroupAdmin(groupname, "Only group admin or superadmin can add registry in group")

	var reg = new(registry.Registry)
	err := json.Unmarshal(c.Ctx.Input.RequestBody, reg)
	if err != nil {
		c.LogAdd(2, "创建镜像仓库[", groupname, "][", reg.Name, "] 失败,[", err.Error(), "]")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}
	err = reg.Add(groupname)
	if err != nil {
		c.LogAdd(2, "创建镜像仓库[", groupname, "][", reg.Name, "] 失败,[", err.Error(), "]")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}
	c.LogAdd(4, "创建镜像仓库[", groupname, "][", reg.Name, "] 成功")
	c.Data["json"] = models.GenerateResponseMsg("Add success")
	c.ServeJSON()
}

// @Title Update Group Registry
// @Description Update group registry
// @Param	token			header	string				true		"The login token"
// @Param	groupname		path 	string				true		"group name"
// @Param	id      		path 	string				true		"registry id"
// @Param	body			body 	registry.Registry	true		"registry info"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /group/:groupname [post]
func (c *RegistryController) UpdateGroupRegistry() {
	reg_id := c.GetString(":id")
	groupname := c.GetString(":groupname")
	if groupname == "" {
		c.LogMod(2, "修改镜像仓库[", reg_id, "] 失败， group无效")
		msg := models.GenerateErrorMsg(404, "invalid group")
		c.Ctx.ResponseWriter.WriteHeader(404)
		c.Data["json"] = msg
		c.ServeJSON()
		return
	}

	c.NeedGroupAdmin(groupname, "Only group admin or superadmin can add registry in group")
	c.Update(groupname)
}

// @Title Update public Registry
// @Description Update public registry
// @Param	token			header	string				true		"The login token"
// @Param	id      		path 	string				true		"registry id"
// @Param	body			body 	registry.Registry	true		"registry info"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /group/:groupname [post]
func (c *RegistryController) UpdatePublicRegistry() {
	c.NeedAdmin("Higher than admin can update public registry")
	c.Update(registry.PUBLIC_REGISTRY)
}

// Put update registry information
// @Title Update
// @Description update the registry
// @Param	id		path 	string			true	"the registry id you want to update"
// @Param	groupname	path 	string		true	"The groupname, the registry belong to"
// @Param	body	body 	registry       	true	"body for registry content"
// @Param	token	header	string			true	"The login token"
// @Success 200 {object} registry.Registry
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:id [put]
func (c *RegistryController) Update(groupname string) {

	reg_id := c.GetString(":id")

	if reg_id == "" {
		c.LogMod(2, "修改镜像仓库[", reg_id, "] 失败， ID无效")
		msg := models.GenerateErrorMsg(404, "invalid registry id")
		c.Ctx.ResponseWriter.WriteHeader(404)
		c.Data["json"] = msg
		c.ServeJSON()
		return
	}

	updateReg := registry.Registry{}
	err := json.Unmarshal(c.Ctx.Input.RequestBody, &updateReg)
	if err != nil {
		c.LogMod(2, "修改镜像仓库[", reg_id, "] 失败，[", err.Error(), "]")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}

	reg := registry.Registry{}
	err = reg.Get(groupname, reg_id)
	if err != nil {
		c.LogMod(2, "修改镜像仓库[", reg_id, "] 失败，记录不存在")
		msg := models.GenerateErrorMsg(500, err.Error())
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = msg
		c.ServeJSON()
		return
	}

	if err := reg.Update(groupname, &updateReg); err != nil {
		c.LogMod(2, "修改镜像仓库[", reg.Name, "] 失败，[", err.Error(), "]")
		msg := models.GenerateErrorMsg(500, "modify fail")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = msg
		c.ServeJSON()
		return
	}

	c.LogMod(4, "修改镜像仓库[", reg.Name, "] 成功")
	c.Data["json"] = updateReg
	c.ServeJSON()
}

// @Title Get Group Registry
// @Description get group registry
// @Param	token	header	string		true		"The login token"
// @Param	groupname		path 	string				true		"group name"
// @Success 200 {object} []registry.Registry
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /group/:groupname [get]
func (c *RegistryController) GetGroupRegistry() {
	c.NeedLogin("")

	groupname := c.GetString(":groupname")
	allreg := registry.GetGroupRegistry(groupname)
	pubreg := registry.GetGroupRegistry(registry.PUBLIC_REGISTRY)
	allreg = append(allreg, pubreg...)
	c.Data["json"] = allreg
	c.ServeJSON()
}

// @Title Delete Group Registry
// @Description delete group registry
// @Param	token			header	string		true		"The login token"
// @Param	groupname		path 	string		true		"group name"
// @Param	address			path 	string		true		"address of registry"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /group/:groupname/:name [delete]
func (c *RegistryController) DeleteGroupRegistry() {
	groupname := c.GetString(":groupname")

	c.NeedGroupAdmin(groupname, "Only group admin or superadmin can delete registry in group")

	var reg = new(registry.Registry)
	reg.ID = c.GetString(":id")
	err := reg.Remove(groupname)
	if err != nil {
		c.LogDel(2, "删除镜像仓库[", groupname, "][", reg.ID, "] 失败")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}

	c.LogDel(4, "删除镜像仓库[", groupname, "][", reg.ID, "] 成功")
	c.Data["json"] = models.GenerateResponseMsg("Delete success")
	c.ServeJSON()
}

// GetRegistry return all registry include group and public registry
// @Title Get Registry
// @Description get registry
// @Param	token	header	string		true		"The login token"
// @Success 200 {object} []registry.Registry
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /all [get]
func (c *RegistryController) GetRegistry() {
	c.NeedLogin("")
	registry := registry.GetAllRegistry()
	c.Data["json"] = registry
	c.ServeJSON()
}

// Total return all registry include group and public registry
// @Title Get Registry number
// @Description gGet Registry number
// @Param	token	header	string		true		"The login token"
// @Param	groupname		path 	string		true		"group name"
// @Success 200 {object} []registry.Registry
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /all [get]
func (c *RegistryController) Total() {
	c.NeedLogin("")
	groupname := c.GetString(":groupname")
	if len(groupname) > 0 {
		c.Data["json"] = registry.CountByGroup(groupname)
	} else {
		c.Data["json"] = registry.CountTotal()
	}

	c.ServeJSON()
}
