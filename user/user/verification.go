package user

import (
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"
	"ufleet/user/auth"
	etcd "ufleet/user/util/etcdclientv3"
	"ufleet/user/util/logs"
	"ufleet/user/util/stringid"
)

//Generate generate new VerificationCode
func (v *VerificationCode) Generate(u *User) {
	v.Code = stringid.GetNumberString(6)
	v.UserName = u.Username
	v.Expirytime = time.Now().Unix() + int64(verifyExpire)
	v.EtcdKey = etcd.EtcdPathJoin([]string{verifyKeyBase, u.Username})
}

//Get get VerificationCode info by VerificationCode string
func (v *VerificationCode) get(username string) bool {
	tt := etcd.EtcdPathJoin([]string{verifyKeyBase, username})
	codeInfo, err := etcd.Client.GetKV(tt)
	if err != nil {
		logs.Critical(err)
		return false
	}

	verify := VerificationCode{}
	err = json.Unmarshal([]byte(codeInfo), &verify)
	if err != nil {
		logs.Critical("Unmarshal VerificationCode info fail.")
		return false
	}
	verify.EtcdKey = tt
	*v = verify
	return true
}

//Save save VerificationCode to etcd
func (v *VerificationCode) save() error {
	content, err := json.Marshal(v)
	if err != nil {
		logs.Critical(err.Error())
		return err
	}

	err = etcd.Client.SetKVWithTTL(v.EtcdKey, string(content), verifyExpire)
	return err
}

//Update update VerificationCode ttl
func (v *VerificationCode) update() error {
	err := etcd.Client.UpdateTTL(v.EtcdKey, verifyExpire)
	return err
}

//Remove remove VerificationCode from etcd
func (v *VerificationCode) remove() error {
	err := etcd.Client.RemoveKey(v.EtcdKey)
	return err
}

//verify the code
func (v *VerificationCode) verify(code string) error {
	if code != v.Code {
		return errors.New("the code invalid.")
	}
	if v.Expirytime < time.Now().Unix() {
		return errors.New("the code time out.")
	}

	return nil
}

func (v *VerificationCode) message() string {
	return fmt.Sprintf("您重置密码的验证码是：【%s】, 有效时间【%d】秒，请知悉！", v.Code, verifyExpire)
}

func (v *VerificationCode) subject() string {
	return fmt.Sprintf("【%s】您重置密码的验证码,【%s】发送,【%d】秒后失效", v.UserName, time.Now().Format("2006-01-02 15:04:05"), verifyExpire)
}

var (
	codeCacheMap = make(map[string]*VerificationCode)
	codeLock     = sync.RWMutex{}
)

func SendRandomStr(username string) error {
	usermap := reloadUserData()
	for _, pu := range usermap {
		if pu.Username == username {
			if pu.SysProfile.AuthType != auth.AUTH_TYPE_LOCAL {
				logs.Error("The user", username, " is ldap user")
				return errors.New("The user" + username + " is ldap user")
			}
			code, err := CreateVerifyCode(pu)
			if err != nil {
				logs.Error("create verify code for [", username, "]fail,as[", err.Error(), "]")
				return err
			}
			subject := code.subject()
			message := code.message()
			err = pu.SendEmail(subject, message)
			if err == nil {
				logs.Info("sent random string to [", username, "]success")
			} else {
				logs.Error("sent random string to [", username, "]fail,as[", err.Error(), "]")
			}
			return err
		}
	}
	return errors.New("The user [" + username + "] not exist")
}

func CreateVerifyCode(u *User) (*VerificationCode, error) {
	code := &VerificationCode{}
	code.Generate(u)
	codeCacheMap[code.UserName] = code
	return code, nil
}

func DeleteVerifyCode(username string) error {
	code, ok := codeCacheMap[username]
	if ok {
		code.remove()
		delete(codeCacheMap, username)
		logs.Debug("delete verify code [", username, "]success")
		return nil
	}

	code = &VerificationCode{}
	if code.get(username) {
		return code.remove()
	} else {
		logs.Error("delete verify code [", username, "]fail,as[code not exist]")
		return errors.New("the code not exist.")
	}
}

func GetVerifyCode(username string) (*VerificationCode, error) {
	code, ok := codeCacheMap[username]
	if ok {
		logs.Debug("get verify code [", username, "]success")
		return code, nil
	}

	code = &VerificationCode{}
	if code.get(username) {
		return code, nil
	} else {
		logs.Error("get verify code [", username, "]fail,as[code not exist]")
		return nil, errors.New("the code not exist.")
	}
}

func ResetPassword(username, password, code string) error {
	verifyCode, err := GetVerifyCode(username)
	if err != nil {
		logs.Error("ResetPassword for[", username, "] fail,as[", err.Error(), "]")
		return err
	}
	err = verifyCode.verify(code)
	if err != nil {
		logs.Warn("ResetPassword for[", username, "] fail,as[", err.Error(), "]")
		return err
	}

	usermap := reloadUserData()
	for _, pu := range usermap {
		if pu.Username == username {
			return pu.PasswordSet(password)
		}
	}
	return errors.New("The user [" + username + "] not exist")
}
