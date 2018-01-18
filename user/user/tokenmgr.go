package user

import (
	"encoding/base64"
	"errors"
	"fmt"
	"github.com/astaxie/beego"
	"strings"
	"sync"
	"time"
	log "ufleet/user/util/logs"
)

var (
	tokenCacheMap = make(map[string]*Token)
	tokenLock     = sync.RWMutex{}
)

func AddToken(token *Token) {
	tokenLock.Lock()
	tokenCacheMap[token.Token] = token
	tokenLock.Unlock()
}

func DeleteToken(token string) (bool, error) {
	tokenLock.Lock()
	defer tokenLock.Unlock()

	t, ok := tokenCacheMap[token]
	if ok {
		err := t.remove()
		delete(tokenCacheMap, token)
		if err != nil {
			return false, errors.New("Clean login info fail")
		} else {
			return true, nil
		}
	}
	t = &Token{}
	if t.get(token) != false {
		t.remove()
		return true, nil
	}
	log.Error("token[", token, "] not exist")
	return true, nil
}

//CheckAndUpdateToken check token by token string ,if exists, update token ttl
func CheckAndUpdateToken(token string) (bool, *Token) {
	tokenLock.Lock()
	defer tokenLock.Unlock()
	t, ok := tokenCacheMap[token]
	if ok {
		log.Debug("update token in cache:", token)
		t.Expirytime = time.Now().Unix() + int64(tokenExpire)
		t.update()
		return true, t
	}

	t = &Token{}
	if t.get(token) != false {
		log.Warn("update token in etcd:", token)
		t.update()
		tokenCacheMap[t.Token] = t
		return true, t
	}

	return false, nil
}

// delete user token from token cache
func DeleteTokenByUserID(user_id string) error {
	token_key := ""
	tokenLock.RLock()
	for key, token := range tokenCacheMap {
		if token.UID == user_id {
			token.remove()
			token_key = key
			break
		}
	}
	tokenLock.RUnlock()

	if token_key != "" {
		tokenLock.Lock()
		delete(tokenCacheMap, token_key)
		tokenLock.Unlock()
	}
	return nil
}

// delete expire token from token cache
func deleteExpiryToken() error {
	keyList := []string{}
	time_now := time.Now().Unix()
	tokenLock.RLock()
	for key, token := range tokenCacheMap {
		if token.Expirytime <= time_now {
			keyList = append(keyList, key)
		}
	}
	tokenLock.RUnlock()
	if len(keyList) == 0 {
		return nil
	}
	tokenLock.Lock()
	defer tokenLock.Unlock()
	for _, token_key := range keyList {
		log.Info(fmt.Sprintf("delete expired token from cache: %s", token_key))
		delete(tokenCacheMap, token_key)
	}

	return nil
}

func check_token_cache() {
	for {
		deleteExpiryToken()
		time.Sleep(time.Duration(10) * time.Second)
	}
}

//VerifyToken verify token exist, if exists, get user by token
func VerifyToken(token string) (*User, error) {
	if token == innerTokenStr {
		return getSuperadmin(), nil
	}

	islogin, t := CheckAndUpdateToken(token)
	if islogin == false {
		return nil, errors.New("check fail")
	}
	u := new(User)
	u.GetByID(t.UID)
	return u, nil
}

func verifySpecialToken(token string) *User {
	if token == beego.AppConfig.String("overrideapitoken") {
		return getSuperadmin()
	}
	return nil
}

func getSuperadmin() *User {
	u := new(User)
	u.GetByName(superadminName)
	return u
}

//VerifyBasicAuth verify basic auth string, check username and password if correct
func VerifyBasicAuth(authStr string) (*User, error) {
	log.Info("basic auth string:", authStr)
	b, err := base64.StdEncoding.DecodeString(authStr)
	if err != nil {
		return nil, err
	}
	pair := strings.SplitN(string(b), ":", 2)
	if len(pair) != 2 {
		return nil, fmt.Errorf("Can not get user and password string")
	}
	username := pair[0]
	password := pair[1]
	return VerifyNameAndPassword(username, password)
}
