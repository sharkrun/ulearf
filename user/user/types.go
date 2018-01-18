package user

import (
	"github.com/astaxie/beego"
	"os"
	etcd "ufleet/user/util/etcdclientv3"
)

var (
	tokenExpire       = beego.AppConfig.DefaultInt("userloginexpire", 600)
	verifyExpire      = beego.AppConfig.DefaultInt("userverifyexpire", 180)
	tokenKeyBase      = etcd.EtcdPathJoin([]string{etcdKeyBase, "user", "token"})
	verifyKeyBase     = etcd.EtcdPathJoin([]string{etcdKeyBase, "user", "verify"})
	innerTokenStr     = beego.AppConfig.String("overrideapitoken")
	messageHubAddress = os.Getenv("MSGHUB_HOST")
)

const loginFailLimit int = 5
const lockGap int64 = 1800

//Token record user login token
type Token struct {
	Token      string `json:"token"`
	EtcdKey    string `json:"-"`
	UID        string `json:"uid"`
	Role       string `json:"role"`
	Expirytime int64  `json:"expiry_time"`
}

//Token record user login token
type VerificationCode struct {
	Code       string `json:"code"`
	EtcdKey    string `json:"-"`
	UserName   string `json:"username"`
	Expirytime int64  `json:"expiry_time"`
}

//LogoutToken recv token to logout user
type LogoutToken struct {
	Token string `json:"token"`
}

var (
	//ShowUserPassword control to show user's encode password in api
	ShowUserPassword = true
	//userMapCache save all user info in mem
	userMapCache map[string]*User
	expirytime   = int64(0)

	etcdKeyBase      = beego.AppConfig.String("etcdbase")
	userKeyBase      = etcd.EtcdPathJoin([]string{etcdKeyBase, "user", "detail"})
	userGroupKeyBase = etcd.EtcdPathJoin([]string{etcdKeyBase, "usergroup"})

	groupUserKeyBase   = "user"
	superadminName     = "admin"
	superadminPassword = "admin"
)

//LoginInfo for receive user login info
type LoginInfo struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type ResetInfo struct {
	LoginInfo
	Veryfycode string `json:"code"`
}

//User for user info
type User struct {
	ID         string        `json:"id"`
	Username   string        `json:"username"`
	Password   string        `json:"password,omitempty"`
	Role       string        `json:"role"`
	Profile    Profile       `json:"profile"`
	SysProfile SystemProfile `json:"systemProfile"`
	Licensed   bool          `json:"licensed"`
}

//ShowUser for user to show in api
type ShowUser struct {
	User
}

//PasswordModify for user to modify password
type PasswordModify struct {
	OldPassword string `json:"oldpassword"`
	Password    string `json:"password"`
}

//Profile for base profile of user
type Profile struct {
	Email    string `json:"email"`
	Nickname string `json:"nickname"`
}

//SystemProfile for system profile of user
type SystemProfile struct {
	IsValid    bool   `json:"isValid"`
	IsActive   bool   `json:"isActive"`
	IsLocked   bool   `json:"isLocked"`
	LockedTime int64  `json:"lockedTime"`
	FailCount  int    `json:"loginFailCount"`
	CreateTime int    `json:"createTime"`
	LastLogin  int    `json:"lastLogin"`
	AuthType   string `json:"authType"`
}

//SearchFilter for search action, to fileter user
type SearchFilter struct {
	ID             string `json:"id"`
	Username       string `json:"username"`
	Email          string `json:"email"`
	AuthType       string `json:"authType"`
	UseActiveCheck bool   `json:"userActiveCheck"`
	IsActive       bool   `json:"isActive"`
	UseValidCheck  bool   `json:"userValidCheck"`
	IsValid        bool   `json:"isValid"`
	GetMulti       bool   `json:"getMulti"`
}

// UserWithGroup type user have group attrbibute
type UserWithGroup struct {
	User
	Group []string `json:"group,omitempty"`
}

// UserGroupRole 2017-04-25 edit by robin, zhiqiang.li@youruncloud.com
type UserGroupRole struct {
	Group string `json:"group,omitempty"`
	Role  string `json:"role,omitempty"`
}
