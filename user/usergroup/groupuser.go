package usergroup

import (
	//"encoding/json"
	//"errors"
	"fmt"
	//"log"
	"path/filepath"

	"ufleet/user/auth"
	"ufleet/user/role"
	"ufleet/user/user"

	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

func checkGroupExistUser(groupname, uid string) bool {
	log.Debug("check uid ", uid, " in usergroup ", groupname)
	groupuserlist := etcd.Client.ListDir(etcd.EtcdPathJoin([]string{usergroupKeyBase, groupname, groupuserKey}))
	ukey := etcd.EtcdPathJoin([]string{usergroupKeyBase, groupname, groupuserKey, uid})
	for _, key := range groupuserlist {
		if key == ukey {
			log.Debug("uid ", uid, " exists in usergroup", groupname)
			return true
		}
	}
	return false
}

//CheckGroupExist check group for existing
func (gu *GroupUser) CheckGroupExist() bool {
	return gu.Group.IsExists()
}

//CheckSelfExistInGroup set user and group in groupuser, then check user in group for existing
func (gu *GroupUser) CheckSelfExistInGroup() bool {
	if gu.CheckGroupExist() == false {
		return false
	}
	if checkGroupExistUser(gu.Group.Name, gu.User.ID) == true {
		return true
	}
	return false
}

//AddToGroup set user, group and role, then add user to group for setting role
func (gu *GroupUser) AddToGroup() error {
	exist := gu.CheckSelfExistInGroup()
	if exist == true {
		return fmt.Errorf("User %s already exists in group %s", gu.User.Username, gu.Group.Name)
	}
	if gu.Role == nil {
		return fmt.Errorf("User %s does not set role in group %s", gu.User.Username, gu.Group.Name)
	}
	gurolekey := etcd.EtcdPathJoin([]string{usergroupKeyBase, gu.Group.Name, groupuserKey, gu.User.ID, userroleKey})
	rolevalue := gu.Role.ToJSON()
	if err := etcd.Client.SetKV(gurolekey, rolevalue); err != nil {
		return err
	}
	return nil
}

//ModifyInGroup set user, group and role, make sure user in group ,then cloud modify user role in group
func (gu *GroupUser) ModifyInGroup() error {
	exist := gu.CheckSelfExistInGroup()
	if exist == false {
		return fmt.Errorf("User %s does not exists in group %s", gu.User.Username, gu.Group.Name)
	}
	if gu.Role == nil {
		return fmt.Errorf("User %s does not set role in group %s", gu.User.Username, gu.Group.Name)
	}
	gurolekey := etcd.EtcdPathJoin([]string{usergroupKeyBase, gu.Group.Name, groupuserKey, gu.User.ID, userroleKey})
	rolevalue := gu.Role.ToJSON()
	if err := etcd.Client.SetKV(gurolekey, rolevalue); err != nil {
		return err
	}
	return nil
}

//DeleteFromGroup set user and group, make sure user in group, then delete user from group
func (gu *GroupUser) DeleteFromGroup() error {
	exist := gu.CheckSelfExistInGroup()
	if exist == false {
		return fmt.Errorf("User %s does not exists in group %s, can not delete", gu.User.Username, gu.Group.Name)
	}
	gukey := etcd.EtcdPathJoin([]string{usergroupKeyBase, gu.Group.Name, groupuserKey, gu.User.ID})
	if err := etcd.Client.RemoveDir(gukey); err != nil {
		return err
	}
	return nil
}

// GetAllGroupname set user , then get all group name which group user in
// 2017-04-18 edit by robin zhiqiang.li@youruncloud.com
func (gu *GroupUser) GetAllGroupname() []string {
	groupList := []string{}
	// /ufleet/usergroup/<groupKey>
	groupKeyList := etcd.Client.ListDir(usergroupKeyBase)
	for _, groupKey := range groupKeyList {
		// /ufleet/usergroup/<groupKey>/user/<userid>, groupUserList = []<userid>
		groupUserList := etcd.Client.ListDir(etcd.EtcdPathJoin([]string{groupKey, groupuserKey}))
		for _, groupUserKey := range groupUserList {
			if gu.User.ID == filepath.Base(groupUserKey) {
				groupList = append(groupList, filepath.Base(groupKey))
			}
		}
	}
	return groupList
}

//CleanInAllGroup set user, then clean user from all group which user in
func (gu *GroupUser) CleanInAllGroup() error {
	gkeylist := etcd.Client.ListDir(usergroupKeyBase)
	for _, gkey := range gkeylist {
		guserlist := etcd.Client.ListDir(etcd.EtcdPathJoin([]string{gkey, groupuserKey}))
		for _, gukey := range guserlist {
			if gu.User.ID == filepath.Base(gukey) {
				if err := etcd.Client.RemoveDir(gukey); err != nil {
					log.Error("remove uid: ", gu.User.ID, "from usergroup", gkey, "fail")
					return err
				}
			}
		}
	}
	return nil
}

//GetByName get groupuser by user name and group name
func (gu *GroupUser) GetByName(username, groupname string) error {
	gu.Group = new(UserGroup)
	if err := gu.Group.Get(groupname); err != nil {
		return err
	}

	u := new(user.User)
	if err := u.GetByName(username); err != nil {
		return err
	}
	gu.User = u
	gu.ShowUser = u.ExportToShow()

	if gu.CheckSelfExistInGroup() == false {
		return fmt.Errorf("User %s does not exist in Usergroup %s", gu.User.Username, gu.Group.Name)
	}
	if _, err := gu.GetRole(); err != nil {
		return err
	}
	return nil
}

//GetByID get groupuser by user id and group name
func (gu *GroupUser) GetByID(uid, groupname string) error {
	gu.Group = new(UserGroup)
	if err := gu.Group.Get(groupname); err != nil {
		return err
	}

	u := new(user.User)
	if err := u.GetByID(uid); err != nil {
		return err
	}
	gu.User = u
	gu.ShowUser = u.ExportToShow()

	if gu.CheckSelfExistInGroup() == false {
		return fmt.Errorf("User %s does not exist in Usergroup %s", gu.User.Username, gu.Group.Name)
	}
	if _, err := gu.GetRole(); err != nil {
		return err
	}
	return nil
}

//GetRole get user role in user group
func (gu *GroupUser) GetRole() (*role.Role, error) {

	if gu.CheckSelfExistInGroup() == false {
		return nil, fmt.Errorf("User %s does not exist in Usergroup %s", gu.User.Username, gu.Group.Name)
	}
	if gu.User.IsSuperAdmin() {
		gu.Role = role.SuperAdmin
		return gu.Role, nil
	}

	if gu.User.IsAdmin() {
		gu.Role = role.GroupAdmin
		return gu.Role, nil
	}

	gurolekey := etcd.EtcdPathJoin([]string{usergroupKeyBase, gu.Group.Name, groupuserKey, gu.User.ID, userroleKey})
	guroleval, err := etcd.Client.GetKV(gurolekey)
	if err != nil {
		return nil, fmt.Errorf("Get User %s's role in Usergroup %s fail", gu.User.Username, gu.Group.Name)
	}
	r := new(role.Role)
	r.FromJSON(guroleval)
	gu.Role = r
	return r, nil
}

//IsSuperAdmin check user if is super admin
func (gu *GroupUser) IsSuperAdmin() bool {
	if gu.User.IsSuperAdmin() == true {
		return true
	}
	return false
}

//IsAdmin check user if is admin
func (gu *GroupUser) IsAdmin() bool {
	if gu.IsSuperAdmin() == true {
		return true
	}
	r, err := gu.GetRole()
	if err != nil {
		return false
	}
	if r.IsSuperAdmin() == true {
		return true
	}
	if r.IsGroupAdmin() == true {
		return true
	}
	return false
}

//AddUserToGroup add user to group
func AddUserToGroup(u *user.User, g *UserGroup, role *role.Role) (bool, error) {
	gu := new(GroupUser)
	gu.Group = g
	gu.User = u
	gu.Role = role
	if err := gu.AddToGroup(); err != nil {
		return false, err
	}
	return true, nil
}

//GetRoleByUsernameInGroup get role by user name and group name
func GetRoleByUsernameInGroup(username string, groupname string) (*role.Role, error) {
	gu := new(GroupUser)

	u := new(user.User)
	if err := u.GetByName(username); err != nil {
		return nil, err
	}
	gu.User = u

	g := new(UserGroup)
	if err := g.Get(groupname); err != nil {
		return nil, err
	}
	gu.Group = g

	r, err := gu.GetRole()
	if err != nil {
		return nil, err
	}
	return r, nil
}

//GetAllUserInGroup get all user in a group
func GetAllUserInGroup(groupname string) ([]*GroupUser, error) {
	retGroupUserList := make([]*GroupUser, 0)
	allukey := etcd.EtcdPathJoin([]string{usergroupKeyBase, groupname, groupuserKey})
	allu := etcd.Client.ListDir(allukey)
	authtype := auth.GetAuthType()
	for _, k := range allu {
		uid := filepath.Base(k)
		u := new(user.User)
		if err := u.GetByID(uid); err != nil {
			return retGroupUserList, err
		}
		if authtype != u.SysProfile.AuthType {
			continue
		}

		gu := new(GroupUser)
		gu.User = u
		gu.ShowUser = u.ExportToShow()
		g := new(UserGroup)
		if err := g.Get(groupname); err != nil {
			return retGroupUserList, err
		}
		gu.Group = g
		gu.GetRole()

		retGroupUserList = append(retGroupUserList, gu)
	}
	return retGroupUserList, nil
}
