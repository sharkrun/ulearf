package user

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	//"log"
	"container/list"
	"github.com/astaxie/beego/logs"
	ufleetSystem "go-ufleetutil/system"
	"strings"
	"time"
	"ufleet/user/auth"
	p "ufleet/user/protocol"
	"ufleet/user/repository"
	"ufleet/user/role"
	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
	"ufleet/user/util/stringid"
)

//InitUser to init user module, read etcd and try set default admin
func InitUser() {
	AddDefaultAdmin()
	go check_token_cache()
	go unlockUser()
}

func unlockUser() {
	var tick = time.Tick(30 * time.Second)
	for {
		select {
		case <-tick:
			doUnlock()
		}
	}
}

func doUnlock() {
	//log.Info("do unlock ... ")
	for _, u := range userMapCache {
		if u.SysProfile.IsLocked && u.SysProfile.LockedTime+lockGap <= time.Now().Unix() {
			u.SysProfile.IsLocked = false
			u.SysProfile.FailCount = 0
			u.Save()
			log.Info(fmt.Sprintf("unlock user id: %s, name: %s", u.ID, u.Username))
		}
	}
}

func ResetAdminPass() {
	log.Info("--------ResetAdminPass at", time.Now().Format("2006-01-02 15:04:05"), "------------")
	userMap := LoadAllFromEtcd()
	for _, pu := range userMap {
		if pu.Username == superadminName {
			pu.PasswordSet(superadminPassword)
			log.Info("--------ResetAdminPass success------------")
			break
		}
	}
}

//AddDefaultAdmin if superadmin does not exist, will create superadmin
func AddDefaultAdmin() {
	var find = false
	userMap := LoadAllFromEtcd()
	for _, pu := range userMap {
		if pu.Username == superadminName {
			find = true
			break
		}
	}
	if find == false {
		var u = new(User)
		u.Username = superadminName
		u.Password = superadminPassword
		u.Role = role.ROLE_SUPERADMIN
		log.Info("Add [superadmin] to local user")
		AddNewUser(u, auth.AUTH_TYPE_LOCAL)
	}
}

func reloadUserData() map[string]*User {
	if expirytime <= time.Now().Unix() {
		userMapCache = LoadAllFromEtcd()
		expirytime = time.Now().Unix() + 10
	}

	return userMapCache
}

func checkLoginFailCount(username string) (*User, p.BaseError) {
	userkeylist := etcd.Client.ListDir(userKeyBase)
	for _, key := range userkeylist {
		log.Debug("checkLoginFailCount Read user key:", key)
		userinfo, err := etcd.Client.GetKV(key)
		if err != nil {
			log.Critical(err)
			continue
		}
		user := new(User)
		err = json.Unmarshal([]byte(userinfo), user)
		if err != nil {
			log.Critical(err)
			continue
		}
		if user.Username == username {
			if user.SysProfile.FailCount >= loginFailLimit {
				return nil, p.BaseError{errors.New("连续登陆失败次数过多"), p.C_LOGIN_FAIL_COUNT_LIMIT}
			} else {
				return user, p.BaseError{nil, p.C_SUCCESS}
			}
		}
	}
	log.Debug("checkLoginFailCount can not find userinfo ", username)
	return nil, p.BaseError{errors.New("用户名或密码错误"), p.C_USERNAME_OR_PASSWD_ERROR}
}

//LoadAllFromEtcd load all user info from etcd and store in UserList
func LoadAllFromEtcd() map[string]*User {
	usermap := make(map[string]*User, 0)
	userkeylist := etcd.Client.ListDir(userKeyBase)
	count := 0

	for _, key := range userkeylist {
		log.Debug("Read user key:", key)
		userinfo, err := etcd.Client.GetKV(key)
		if err != nil {
			log.Critical(err)
			continue
		}
		user := new(User)
		err = json.Unmarshal([]byte(userinfo), user)
		if err != nil {
			log.Critical(err)
			continue
		}
		usermap[user.ID] = user
		count++
	}
	log.Debug("Read ", count, " user from etcd")
	return usermap
}

//SaveAllToEtcd save all UserList info to etcd
// func SaveAllToEtcd() int {
// 	count := 0
// 	for _, u := range UserList {
// 		u.Save()
// 		count++
// 	}
// 	log.Info("Write ", count, " user to etcd")
// 	return count
// }

//AddNewUser add new user by auth type
func AddNewUser(u *User, authtype string) (string, error) {
	usermap := reloadUserData()
	for _, user := range usermap {
		if u.Username == user.Username && user.SysProfile.AuthType == authtype {
			return "", errors.New(fmt.Sprint("User ", user.Username, " already exists"))
		}
	}
	u.ID = stringid.GenerateID()
	u.SysProfile.IsActive = true
	u.SysProfile.IsValid = true
	u.SysProfile.CreateTime = int(time.Now().Unix())
	u.SysProfile.AuthType = authtype
	u.PasswordSet(u.Password)
	u.Save()
	expirytime = 0
	return u.ID, nil
}

//GetAllShowUsers get all user in show user format
func GetAllShowUsers() []*ShowUser {
	usermap := reloadUserData()
	authtype := auth.GetAuthType()
	showUserList := make([]*ShowUser, 0)
	for _, user := range usermap {
		if user.SysProfile.IsActive == false {
			continue
		}
		if user.SysProfile.IsValid == false {
			continue
		}
		if user.SysProfile.AuthType != authtype {
			continue
		}

		showUserList = append(showUserList, user.ExportToShow())
	}
	return showUserList
}

//GetAllShowUsers get all user in show user format
func GetAdminUsers() []*ShowUser {
	usermap := reloadUserData()
	authtype := auth.GetAuthType()
	showUserList := make([]*ShowUser, 0)
	for _, user := range usermap {
		if user.SysProfile.IsActive == false {
			continue
		}
		if user.SysProfile.IsValid == false {
			continue
		}
		if user.SysProfile.AuthType != authtype {
			continue
		}
		if user.IsAdmin() == false {
			continue
		}

		showUserList = append(showUserList, user.ExportToShow())
	}
	return showUserList
}

//ExportToShow export user to show user format
func (u *User) ExportToShow() *ShowUser {
	var su ShowUser
	su.ID = u.ID
	su.Username = u.Username
	su.Role = u.Role
	if ShowUserPassword == true {
		su.Password = u.Password
	}
	su.Profile = u.Profile
	su.SysProfile = u.SysProfile
	return &su
}

//Get get user info by id
func (u *User) get(id string) error {
	ukey := etcd.EtcdPathJoin([]string{userKeyBase, id})
	uinfo, err := etcd.Client.GetKV(ukey)
	if err != nil {
		log.Critical(err)
		return errors.New("User not exists")
	}
	getu := &User{}
	err = json.Unmarshal([]byte(uinfo), getu)
	if err != nil {
		log.Critical(err)
		return errors.New("User data error")
	}
	if getu.SysProfile.IsValid == false {
		return errors.New("User already delete")
	}
	if getu.SysProfile.IsActive == false {
		return errors.New("User is inactive")
	}
	*u = *getu
	return nil
}

//GetById get user info by id
func (u *User) GetByID(id string) error {
	usermap := reloadUserData()
	user, ok := usermap[id]
	if ok {
		if user.SysProfile.IsValid == false {
			return errors.New("User already delete")
		}
		if user.SysProfile.IsActive == false {
			return errors.New("User is inactive")
		}
		*u = *user
		return nil
	}
	return u.get(id)
}

//GetByName get user info by user name
func (u *User) GetByName(name string) error {
	find := false
	usermap := reloadUserData()
	for _, user := range usermap {
		if user.Username == name {
			if user.SysProfile.IsValid == false {
				return errors.New("User already delete")
			}
			if user.SysProfile.IsActive == false {
				return errors.New("User is inactive")
			}
			*u = *user
			find = true
			break
		}
	}
	if find == false {
		return errors.New("User is not found")
	}
	return nil

}

//IsSuperAdmin check user if is super admin
func (u *User) IsSuperAdmin() bool {
	return u.Role == role.ROLE_SUPERADMIN
}

//IsAdmin check user if is admin
func (u *User) IsAdmin() bool {
	return u.Role == role.ROLE_ADMIN
}

//IsAdmin check user if is admin
func (u *User) HasAdminPower() bool {
	return u.Role == role.ROLE_ADMIN || u.Role == role.ROLE_SUPERADMIN
}

//PasswordSet set user password
func (u *User) PasswordSet(password string) error {
	if u.SysProfile.AuthType == auth.AUTH_TYPE_LDAP {
		return errors.New("ldap account can not set password")
	}

	u.Password = passwordEncode(u.Username, password)
	return u.Save()
}

//PasswordVerify verify password if is correct
func (u *User) PasswordVerify(password string) bool {
	if u.SysProfile.AuthType == auth.AUTH_TYPE_LDAP {
		return false
	}
	encodepwd := passwordEncode(u.Username, password)
	return encodepwd == u.Password
}

//Delete delete user
func (u *User) Delete() error {
	repo := repository.Repository{}
	err := repo.RemoveUserRepo(u.Username)
	if err != nil {
		log.Critical("remove user all repository fail,as [", err, "]")
	}

	if u.Username == superadminName {
		return nil
	}
	u.SysProfile.IsValid = false
	return u.Save()
}

//Clean clean user info
func (u *User) Clean() error {
	if u.Username == superadminName {
		return nil
	}
	if len(u.ID) == 0 {
		return fmt.Errorf("Unkown user")
	}
	k := etcd.EtcdPathJoin([]string{userKeyBase, u.ID})
	err := etcd.Client.RemoveKey(k)
	if err != nil {
		log.Critical("Clean user fail, id:", u.ID)
	}
	expirytime = 0
	return err
}

//Deactive deactive user
func (u *User) Deactive() error {
	if u.Username == superadminName {
		return nil
	}
	DeleteTokenByUserID(u.ID)

	u.SysProfile.IsActive = false
	return u.Save()
}

//Active active user
func (u *User) Active() error {

	u.SysProfile.IsActive = true
	u.SysProfile.IsValid = true
	return u.Save()
}

func (u *User) Unlock() error {
	u.SysProfile.IsLocked = false
	u.SysProfile.FailCount = 0
	return u.Save()
}

//Update update user info
func (u *User) Update(uu *User) (err error) {
	if uu.Password != "" {
		u.Password = passwordEncode(uu.Username, uu.Password)
	}
	if uu.Profile.Email != "" {
		u.Profile.Email = uu.Profile.Email
	}
	if uu.Profile.Nickname != "" {
		u.Profile.Nickname = uu.Profile.Nickname
	}
	if role.IsValidRole(uu.Role) && uu.Role != u.Role {
		u.Role = uu.Role
	}
	u.Save()
	return nil
}

//UpdatePassword update user password
func (u *User) UpdatePassword(mpwd *PasswordModify) (err error) {
	if u.SysProfile.AuthType == auth.AUTH_TYPE_LDAP {
		return errors.New("ldap account can not modify password")
	}
	if ret := u.PasswordVerify(mpwd.OldPassword); ret == false {
		return errors.New("old password verify error")
	}
	if err := u.PasswordSet(mpwd.Password); err != nil {
		return err
	}
	return nil
}

//UpdatePassword update user password
func (u *User) UpdateProfile(profile *Profile) (err error) {
	if len(profile.Email) > 0 {
		u.Profile.Email = profile.Email
	}

	if len(profile.Nickname) > 0 {
		u.Profile.Nickname = profile.Nickname
	}

	return u.Save()
}

func (u *User) CountLoginFailTimes() error {
	u.SysProfile.FailCount += 1
	if u.SysProfile.FailCount >= loginFailLimit {
		u.SysProfile.IsLocked = true
		u.SysProfile.LockedTime = time.Now().Unix()
	}
	return u.Save()
}

//Save save user info to etcd
func (u *User) Save() error {
	k := etcd.EtcdPathJoin([]string{userKeyBase, u.ID})
	v, err := json.Marshal(u)
	if err != nil {
		log.Critical(err)
		return err
	}
	err = etcd.Client.SetKV(k, string(v))
	if err != nil {
		log.Critical(err)
		return err
	}
	expirytime = 0
	return nil
}

func VerifyNameAndPassword(username, password string) (*User, error) {
	usermap := reloadUserData()
	authtype := auth.GetAuthType()
	for _, pu := range usermap {
		if pu.Username == username {
			if authtype == auth.AUTH_TYPE_LOCAL {
				verifyret := pu.PasswordVerify(password)
				if verifyret == true {
					return pu, nil
				}
			}
			if authtype == auth.AUTH_TYPE_LDAP {
				_, ok := auth.LdapVerify(username, password)
				if ok == true {
					return pu, nil
				}
			}
		}
	}
	return nil, fmt.Errorf("Can not find user")
}

//Login user login by username and password
func Login(username, password string) (*Token, p.BaseError) {
	user, berr := checkLoginFailCount(username)
	if berr.Errs != nil {
		return nil, berr
	}
	token, berr := verify(username, password)

	//用户名密码不匹配，统计错误次数
	if berr.StatusDtl == p.C_USERNAME_OR_PASSWD_ERROR {
		user.CountLoginFailTimes()
		return nil, berr
	}

	if berr.Errs == nil {
		AddToken(token)
		user.SysProfile.FailCount = 0
		user.Save()
	}

	// 不属于任何用户组的普通用户不能登录
	u := new(User)
	u.GetByID(token.UID)
	groups := u.GetUserGroup()
	// 身份是管理员的用户不需要校验
	if u.Role != role.ROLE_SUPERADMIN && u.Role != role.ROLE_ADMIN {
		if len(groups) == 0 {
			logs.Info(fmt.Sprintf("user %s role: %s", u.ID, u.Role))
			return nil, p.BaseError{errors.New("该用户无用户组"), p.C_USER_NO_GROUP}
		}
	}

	return token, berr
}

func verify(username, password string) (*Token, p.BaseError) {
	usermap := reloadUserData()
	for _, pu := range usermap {
		if pu.Username == username {
			if pu.IsSuperAdmin() {
				if pu.SysProfile.AuthType == auth.AUTH_TYPE_LOCAL {
					return LoginLocalAuth(username, password)
				}
				if pu.SysProfile.AuthType == auth.AUTH_TYPE_LDAP {
					return LoginLdapAuth(username, password)
				}
			}
		}
	}

	authtype := auth.GetAuthType()
	if authtype == auth.AUTH_TYPE_LOCAL {
		return LoginLocalAuth(username, password)
	} else if authtype == auth.AUTH_TYPE_LDAP {
		return LoginLdapAuth(username, password)
	} else {
		return nil, p.BaseError{errors.New("auth type error"), p.C_AUTH_TYPE_UNKNOWN}
	}
}

//LoginLocalAuth login handle for local auth user
func LoginLocalAuth(username, password string) (*Token, p.BaseError) {
	usermap := reloadUserData()
	for _, u := range usermap {
		if u.Username == username {
			if u.SysProfile.AuthType != auth.AUTH_TYPE_LOCAL {
				continue
			}
			if u.SysProfile.IsValid == false {
				return nil, p.BaseError{errors.New("非法用户"), p.C_SYSTEMPROFILE_INVALID}
			}
			if u.SysProfile.IsActive == false {
				return nil, p.BaseError{errors.New("未激活用户"), p.C_INACTIVE_USER}
			}
			loginret := u.PasswordVerify(password)
			if loginret == true {
				u.SysProfile.LastLogin = int(time.Now().Unix())
				u.Save()
				token := &Token{}
				token.Generate(u)
				token.save()
				return token, p.BaseError{nil, p.C_SUCCESS}
			} else {
				return nil, p.BaseError{errors.New("用户名或密码错误"), p.C_USERNAME_OR_PASSWD_ERROR}
			}
		}
	}
	return nil, p.BaseError{errors.New("用户名不存在"), p.C_USERNAME_NOT_EXIST}
}

//LoginLdapAuth login handle for ldap auth user
func LoginLdapAuth(username, password string) (*Token, p.BaseError) {
	ldapuser, ok := auth.LdapVerify(username, password)
	if ok == false {
		return nil, p.BaseError{errors.New("用户名或密码错误"), p.C_USERNAME_OR_PASSWD_ERROR}
	}
	var u *User
	usermap := reloadUserData()
	for _, pu := range usermap {
		if pu.Username == ldapuser.Username {
			if pu.SysProfile.AuthType != auth.AUTH_TYPE_LDAP {
				continue
			}
			if pu.SysProfile.IsValid == false {
				return nil, p.BaseError{errors.New("非法用户"), p.C_SYSTEMPROFILE_INVALID}
			}
			if pu.SysProfile.IsActive == false {
				return nil, p.BaseError{errors.New("未激活用户"), p.C_INACTIVE_USER}
			}
			u = pu
			break
		}
	}
	if u == nil {
		u = new(User)
		u.Username = ldapuser.Username
		u.Profile.Nickname = strings.Trim(ldapuser.Name, " ")
		u.Profile.Email = ldapuser.Email
		if ldapuser.IsAdmin {
			u.Role = role.ROLE_SUPERADMIN
		} else {
			u.Role = role.ROLE_GROUP_USER
		}

		AddNewUser(u, auth.AUTH_TYPE_LDAP)
	}
	u.SysProfile.LastLogin = int(time.Now().Unix())
	u.Save()
	token := &Token{}
	token.Generate(u)
	token.save()
	return token, p.BaseError{nil, p.C_SUCCESS}
}

//Logout logout user
func Logout(token string) (bool, error) {
	return DeleteToken(token)
}

func passwordEncode(name string, password string) string {
	hs := sha256.New()
	hs.Write([]byte(strings.Join([]string{name, password}, "cicd-password-salt")))
	md := hs.Sum(nil)
	mdStr := hex.EncodeToString(md)
	return "sha256:" + mdStr
}

//SearchFilter to search user by fileter
func SearchUser(filter *SearchFilter) ([]*User, error) {
	resultlist := make([]*User, 0)
	if filter == nil {
		return resultlist, errors.New("No search filter")
	}
	alllist := list.New()
	usermap := reloadUserData()
	for _, u := range usermap {
		alllist.PushBack(u)
	}
	var n *list.Element
	if len(filter.ID) != 0 {
		for e := alllist.Front(); e != nil; e = n {
			n = e.Next()
			if e.Value.(*User).ID != filter.ID {
				alllist.Remove(e)
			}
		}
	}
	if len(filter.Username) != 0 {
		for e := alllist.Front(); e != nil; e = n {
			n = e.Next()
			if e.Value.(*User).Username != filter.Username {
				alllist.Remove(e)
			}
		}
	}
	if len(filter.Email) != 0 {
		for e := alllist.Front(); e != nil; e = n {
			n = e.Next()
			if e.Value.(*User).Profile.Email != filter.Email {
				alllist.Remove(e)
			}
		}
	}
	if len(filter.AuthType) != 0 {
		for e := alllist.Front(); e != nil; e = n {
			n = e.Next()
			if e.Value.(*User).SysProfile.AuthType != filter.AuthType {
				alllist.Remove(e)
			}
		}
	}
	if filter.UseActiveCheck {
		for e := alllist.Front(); e != nil; e = n {
			n = e.Next()
			if e.Value.(*User).SysProfile.IsActive != filter.IsActive {
				alllist.Remove(e)
			}
		}
	}
	if filter.UseValidCheck {
		for e := alllist.Front(); e != nil; e = n {
			n = e.Next()
			if e.Value.(*User).SysProfile.IsValid != filter.IsValid {
				alllist.Remove(e)
			}
		}
	}
	if filter.GetMulti {
		for e := alllist.Front(); e != nil; e = e.Next() {
			resultlist = append(resultlist, e.Value.(*User))
		}
	} else {
		e := alllist.Front()
		if e != nil {
			resultlist = append(resultlist, e.Value.(*User))
		}
	}

	return resultlist, nil
}

//LdapUserIsExistInSystem check ldap user in current system
func LdapUserIsExistInSystem(lu *auth.LdapUser) bool {
	f := new(SearchFilter)
	f.Username = lu.Username
	f.AuthType = auth.AUTH_TYPE_LDAP
	f.GetMulti = false
	ulist, err := SearchUser(f)
	if err != nil {
		log.Critical("Search user error:", err)
		return false
	}
	if len(ulist) != 0 {
		lu.IsInSystem = true
		return true
	}
	return false
}

//LdapUserAddToSystem add ldap user to system
func LdapUserAddToSystem(lu *auth.LdapUser) (*User, error) {
	if LdapUserIsExistInSystem(lu) == true {
		return nil, fmt.Errorf("User %s already exists in system", lu.Username)
	}
	u := new(User)
	u.Username = lu.Username
	u.Profile.Nickname = strings.Trim(lu.Name, " ")
	u.Profile.Email = lu.Email
	if lu.IsAdmin {
		u.Role = role.ROLE_SUPERADMIN
	} else {
		u.Role = role.ROLE_GROUP_USER
	}

	uid, err := AddNewUser(u, auth.AUTH_TYPE_LDAP)
	if err == nil {
		u.ID = uid
	}
	return u, err
}

// GetUserGroup get a user's all group name
// 2017-03-20 edit by robin zhiqiang.li@youruncloud.com
func (u *User) GetUserGroup() []string {
	groupList := []string{}
	// /ufleet/usergroup/<group>, groupKey = <group>, groupKeyList = []groupKey
	groupKeyList := etcd.Client.ListDir(userGroupKeyBase)
	for _, groupKey := range groupKeyList {
		// /ufleet/usergroup/<group>/user/<user>, groupUserKey = <user>,
		// groupUserList = []groupUserKey
		groupUserList := etcd.Client.ListDir(
			etcd.EtcdPathJoin([]string{groupKey, groupUserKeyBase}),
		)
		for _, groupUserKey := range groupUserList {
			if u.ID == filepath.Base(groupUserKey) {
				groupList = append(groupList, filepath.Base(groupKey))
			}
		}
	}
	return groupList
}

// CheckUserStatus check if user is available
// 2017-03-20 edit by robin zhiqiang.li@youruncloud.com
func (u *User) CheckUserStatus() error {
	if !u.SysProfile.IsValid {
		return errors.New("User already delete")
	}
	if !u.SysProfile.IsActive {
		return errors.New("User is inactive")
	}

	return nil
}

// GetUserWithGroup get user by id with group field
// 2017-03-20 edit by robin zhiqiang.li@youruncloud.com
func (u *User) GetUserWithGroup(id string) (UserWithGroup, error) {
	user := &User{}
	userWithGroups := UserWithGroup{}

	userEtcdKey := etcd.EtcdPathJoin([]string{userKeyBase, id})
	userEtcdValue, err := etcd.Client.GetKV(userEtcdKey)
	if err != nil {
		return userWithGroups, errors.New("User not exists")
	}
	err = json.Unmarshal([]byte(userEtcdValue), user)
	if err != nil {
		return userWithGroups, errors.New("User data error")
	}
	err = user.CheckUserStatus()
	if err != nil {
		return userWithGroups, err
	}
	userWithGroups.User = *user
	userWithGroups.Group = u.GetUserGroup()
	return userWithGroups, nil
}

// GetAllUserWithGroup get all users with group fields
// 2017-03-20 edit by robin zhiqiang.li@youruncloud.com
func (u *User) GetAllUserWithGroup() ([]UserWithGroup, error) {
	usermap := reloadUserData()
	userWithGroupsList := []UserWithGroup{}
	for _, user := range usermap {
		err := user.CheckUserStatus()
		if err != nil {
			continue
		}
		userWithGroups, err := user.GetUserWithGroup(user.ID)
		if err != nil {
			continue
		}
		userWithGroupsList = append(userWithGroupsList, userWithGroups)
	}
	return userWithGroupsList, nil
}

// GetAllUserWithGroup get all users with group fields
// 2017-03-20 edit by robin zhiqiang.li@youruncloud.com
func (u *User) SendEmail(subject, msg string) error {
	if u.Profile.Email == "" {
		return errors.New("The user [" + u.Username + "] email invalid")
	}

	mailClient := ufleetSystem.NewMailClient(messageHubAddress)
	mailClient.Content = msg
	mailClient.Subject = subject
	mailClient.EmailList = []string{u.Profile.Email}
	return mailClient.Send(innerTokenStr)
}
