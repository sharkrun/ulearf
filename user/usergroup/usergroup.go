package usergroup

import (
	"encoding/json"
	"errors"
	"fmt"
	"time"
	//"log"
	"path/filepath"
	//"strings"

	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

func AddDefaultGroup() {
	var g = new(UserGroup)
	g.Name = "default"
	g.Describe = "Default Group"
	g.SetUserGroupCreateTime()
	if g.IsExists() == false {
		log.Info("Add [default] to group list")
		g.Save()
	}
}

// SetUserGroupCreateTime set usergroup createtime field
func (g *UserGroup) SetUserGroupCreateTime() {
	g.CreateTime = time.Now().Unix()
}

// SetUserGroupName set usergroup createtime field
func (g *UserGroup) SetUserGroupName(name string) {
	g.Name = name
}

// SetUserGroupDescribe set usergroup createtime field
func (g *UserGroup) SetUserGroupDescribe(describe string) {
	g.Describe = describe
}

func (g *UserGroup) Get(name string) error {
	gkey := etcd.EtcdPathJoin([]string{usergroupKeyBase, name, usergroupDetailKey})
	ginfo, err := etcd.Client.GetKV(gkey)
	if err != nil {
		log.Critical(err)
		return errors.New(fmt.Sprint("Usergroup ", name, " does not exist"))
	}
	getg := &UserGroup{}
	err = json.Unmarshal([]byte(ginfo), getg)
	if err != nil {
		log.Critical(err)
		return errors.New("Usergroup data error")
	}
	*g = *getg
	return nil
}

func (g *UserGroup) Delete() error {
	if g.IsExists() == false {
		return errors.New(fmt.Sprint("Usergroup ", g.Name, " does not exist"))
	}
	k := etcd.EtcdPathJoin([]string{usergroupKeyBase, g.Name})
	etcd.Client.RemoveDir(k)
	gg := new(Group)
	gg.Name = g.Name
	gg.Delete()
	return nil
}

func (g *UserGroup) Update() (err error) {
	if g.IsExists() == false {
		return errors.New(fmt.Sprint(" Usergroup ", g.Name, " does not exist"))
	}
	return g.Save()
}

func (g *UserGroup) Add() (err error) {
	if g.IsExists() == true {
		return errors.New(fmt.Sprint(" Usergroup ", g.Name, " exists"))
	}
	return g.Save()
}

func (g *UserGroup) Save() error {
	k := etcd.EtcdPathJoin([]string{usergroupKeyBase, g.Name, usergroupDetailKey})
	g.SetUserGroupCreateTime()
	v, err := json.Marshal(g)
	if err != nil {
		log.Critical(err)
		return err
	}
	err = etcd.Client.SetKV(k, string(v))
	if err != nil {
		log.Critical(err)
		return err
	}
	addUserGroupToGroup(g.Name, g.Name)
	return nil
}

func (g *UserGroup) IsExists() bool {
	if len(g.Name) == 0 {
		return false
	}
	usergroupkeylist := etcd.Client.ListDir(usergroupKeyBase)
	for _, k := range usergroupkeylist {
		if filepath.Base(k) == g.Name {
			return true
		}
	}
	return false
}

func IsUserGroupExist(name string) bool {
	g := &UserGroup{}
	g.Name = name
	return g.IsExists()
}

func GetAllUserGroup() []*UserGroup {
	allug := make([]*UserGroup, 0)
	usergroupkeylist := etcd.Client.ListDir(usergroupKeyBase)
	for _, k := range usergroupkeylist {
		gname := filepath.Base(k)
		g := new(UserGroup)
		if err := g.Get(gname); err != nil {
			log.Critical(err)
			continue
		}
		allug = append(allug, g)
	}
	return allug
}

// GetUserGroups get all usergroups
func GetUserGroups() []UserGroup {
	userGroups := []UserGroup{}
	userGroupKeys := etcd.Client.ListDir(usergroupKeyBase)
	for _, k := range userGroupKeys {
		groupName := filepath.Base(k)
		userGroup := UserGroup{}
		userGroup, err := GetUserGroup(groupName)
		if err != nil {
			continue
		}
		userGroups = append(userGroups, userGroup)
	}
	return userGroups
}

// GetUserGroup get a specfic usergroup by groupname
func GetUserGroup(name string) (UserGroup, error) {
	userGroup := UserGroup{}
	key := etcd.EtcdPathJoin([]string{usergroupKeyBase, name, usergroupDetailKey})
	groupInfo, err := etcd.Client.GetKV(key)
	if err != nil {
		return userGroup, errors.New(fmt.Sprint("Usergroup ", name, " does not exist"))
	}
	err = json.Unmarshal([]byte(groupInfo), &userGroup)
	if err != nil {
		return userGroup, errors.New("Parser usergroup data error")
	}
	users, err := GetAllUserInGroup(userGroup.Name)
	if err != nil {
		return userGroup, err
	}
	userGroup.UserCount = len(users)
	return userGroup, nil
}
