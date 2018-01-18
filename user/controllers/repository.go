package controllers

import (
	"encoding/json"
	"ufleet/user/models"
	"ufleet/user/repository"
)

// Operations about Repository
type RepositoryController struct {
	baseController
}

// @Title Get
// @Description get repository by uid
// @Param	id		path 	string	true		"The key for staticblock"
// @Param	token	header	string	true		"The login token"
// @Success 200 {object} repository.Repository
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:id [get]
func (c *RepositoryController) Get() {
	c.NeedLogin("")

	repo_id := c.GetString(":id")

	var repo = new(repository.Repository)
	if repo_id == "" {
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = "invalid id"
		c.ServeJSON()
		return
	}

	err := repo.Get(c.User.Username, repo_id)
	if err != nil {
		c.Logfind(2, "读取代码仓库信息失败，[", err.Error(), "]")
		msg := models.GenerateErrorMsg(500, err.Error())
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = msg
	} else {
		c.Data["json"] = repo
	}
	c.ServeJSON()
}

// @Title Add  Repository
// @Description add repository
// @Param	token			header	string			    	true		"The login token"
// @Param	body			body 	repository.Repository	true		"repository info"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router / [post]
func (c *RepositoryController) Post() {
	c.NeedLogin("")

	var repo = new(repository.Repository)
	err := json.Unmarshal(c.Ctx.Input.RequestBody, repo)
	if err != nil {
		c.LogAdd(2, "创建代码仓库失败，数据无法解析")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}
	err = repo.Add(c.User.Username)
	if err != nil {
		c.LogAdd(2, "创建代码仓库失败，[", err.Error(), "]")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}

	c.LogAdd(4, "创建代码仓库[", repo.Name, "] 成功")
	c.Data["json"] = models.GenerateResponseMsg("Add success")
	c.ServeJSON()
}

// Put update repository information
// @Title Update
// @Description update the repository
// @Param	id		path 	string				true	"The uid you want to update"
// @Param	body	body 	repository       	true	"body for repository content"
// @Param	token	header	string				true	"The login token"
// @Success 200 {object} repository.Repository
// @Failure 403 {object} models.ErrorMsg
// @Failure 404 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /:id [put]
func (c *RepositoryController) Put() {
	c.NeedLogin("")

	repo_id := c.GetString(":id")

	if repo_id == "" {
		c.LogMod(2, "修改代码仓库[", repo_id, "] 失败， ID无效")
		msg := models.GenerateErrorMsg(404, "repository id not found")
		c.Ctx.ResponseWriter.WriteHeader(404)
		c.Data["json"] = msg
		c.ServeJSON()
		return
	}

	updateRepo := repository.Repository{}
	err := json.Unmarshal(c.Ctx.Input.RequestBody, &updateRepo)
	if err != nil {
		c.LogMod(2, "修改代码仓库[", repo_id, "] 失败，[", err.Error(), "]")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}

	repo := repository.Repository{}
	err = repo.Get(c.User.Username, repo_id)
	if err != nil {
		c.LogMod(2, "修改代码仓库[", repo_id, "] 失败，记录不存在")
		msg := models.GenerateErrorMsg(500, err.Error())
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = msg
		c.ServeJSON()
		return
	}

	if err := repo.Update(c.User.Username, &updateRepo); err != nil {
		c.LogMod(2, "修改代码仓库[", repo.Name, "] 失败，[", err.Error(), "]")
		msg := models.GenerateErrorMsg(500, "modify fail")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = msg
		c.ServeJSON()
		return
	}

	c.LogMod(4, "修改代码仓库[", repo.Name, "] 成功")
	c.Data["json"] = updateRepo
	c.ServeJSON()
}

// @Title Get  Repository
// @Description get user self repository
// @Param	token	header	string		true		"The login token"
// @Success 200 {object} []repository.Repository
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router / [get]
func (c *RepositoryController) GetRepository() {
	c.NeedLogin("")

	c.Data["json"] = repository.GetUserRepository(c.User.Username)
	c.ServeJSON()
}

// @Title Get  GetUserRepository
// @Description get user repository
// @Param	token	header	string		true		"The login token"
// @Success 200 {object} []repository.Repository
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /user/:username [get]
func (c *RepositoryController) GetUserRepository() {
	c.NeedLogin("")

	username := c.GetString(":username")
	if c.User.HasAdminPower() == false && c.User.Username != username {
		c.Logfind(2, "读取[", username, "]代码仓库列表失败，[权限不足]")
		msg := models.GenerateErrorMsg(403, "admin or user himself can get the repository info")
		c.Ctx.ResponseWriter.WriteHeader(403)
		c.Data["json"] = msg
		c.ServeJSON()
		return
	}

	c.Data["json"] = repository.GetUserRepository(username)
	c.ServeJSON()
}

// @Title Delete  Repository
// @Description delete group repository
// @Param	token			header	string		true		"The login token"
// @Param	username		path 	string		true		"group name"
// @Param	address			path 	string		true		"address of repository"
// @Success 200 {object} models.ResponseMsg
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /group/:username/:name [delete]
func (c *RepositoryController) Delete() {
	c.NeedLogin("")

	var repo = new(repository.Repository)
	repo.ID = c.GetString(":id")
	err := repo.Remove(c.User.Username)
	if err != nil {
		c.LogDel(2, "删除代码仓库[", repo.ID, "] 失败,[", err.Error(), "]")
		c.Ctx.ResponseWriter.WriteHeader(500)
		c.Data["json"] = models.GenerateErrorMsg(500, err.Error())
		c.ServeJSON()
		return
	}

	c.LogDel(4, "删除代码仓库[", repo.ID, "] 成功")
	c.Data["json"] = models.GenerateResponseMsg("Delete success")
	c.ServeJSON()
}

// GetAllRepository return all repository repository
// @Title Get GetAllRepository
// @Description get repository
// @Param	token	header	string		true		"The login token"
// @Success 200 {object} []repository.Repository
// @Failure 403 {object} models.ErrorMsg
// @Failure 500 {object} models.ErrorMsg
// @router /all [get]
func (c *RepositoryController) GetAllRepository() {
	c.NeedAdmin("Higher than admin can get all repository")

	repository := repository.GetAllRepository()
	c.Data["json"] = repository
	c.ServeJSON()
}
