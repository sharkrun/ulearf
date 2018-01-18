package usergroup

import (
	"encoding/json"
	"errors"
	//"log"
	"path/filepath"
	//"strings"
	"fmt"

	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

//Delete group tree in etcd
func (g *Group) Delete() error {
	if g.IsExists() == false {
		return errors.New(fmt.Sprint("Group ", g.Name, " does not exist"))
	}
	k := etcd.EtcdPathJoin([]string{groupKeyBase, g.Name})
	err := etcd.Client.RemoveDir(k)
	if err != nil {
		log.Critical(err)
		return err
	}
	return nil
}

//Save group tree in etcd
func (g *Group) Save() error {
	if g.IsExists() == true {
		return nil
	}
	k := etcd.EtcdPathJoin([]string{groupKeyBase, g.Name})
	err := etcd.Client.MakeDir(k)
	if err != nil {
		log.Critical(err)
		return err
	}
	return nil
}

//IsExists check group for existing, check from etcd
func (g *Group) IsExists() bool {
	if len(g.Name) == 0 {
		return false
	}
	groupkeylist := etcd.Client.ListDir(groupKeyBase)
	for _, k := range groupkeylist {
		if filepath.Base(k) == g.Name {
			return true
		}
	}
	return false
}

//IsGroupExist check group name for existing
func IsGroupExist(name string) bool {
	g := new(Group)
	g.Name = name
	return g.IsExists()
}

func addUserGroupToGroup(groupname string, usergroupname string) error {
	g := &Group{}
	g.Name = groupname
	if g.IsExists() == false {
		g.Save()
	}
	k := etcd.EtcdPathJoin([]string{groupKeyBase, g.Name, groupUserGroupKey})
	type groupUsergroup struct {
		ID string `json:"id"`
	}
	var userg groupUsergroup
	userg.ID = usergroupname
	v, err := json.Marshal(userg)
	if err != nil {
		log.Critical(err)
		return err
	}
	etcd.Client.SetKV(k, string(v))
	return nil
}

func GetAllGroupName() []string {
	groupList := []string{}

	groupKeyList := etcd.Client.ListDir(usergroupKeyBase)
	for _, groupKey := range groupKeyList {
		groupList = append(groupList, filepath.Base(groupKey))
	}
	return groupList
}
