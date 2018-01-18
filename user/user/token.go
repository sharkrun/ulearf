package user

import (
	"crypto/sha1"
	"encoding/hex"
	"fmt"
	"strings"
	"time"

	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

//Generate generate new token
func (t *Token) Generate(u *User) {
	ts := time.Now().Unix()
	hs := sha1.New()
	hs.Write([]byte(strings.Join([]string{u.Username, fmt.Sprintf("%d", ts)}, "")))
	md := hs.Sum(nil)
	mdStr := hex.EncodeToString(md)
	log.Debug("user ", u.ID, " generate token", mdStr)
	t.Token = mdStr
	t.UID = u.ID
	t.Role = u.Role
	t.Expirytime = ts + int64(tokenExpire)
	t.EtcdKey = etcd.EtcdPathJoin([]string{tokenKeyBase, t.Token})
}

//Get get token info by token string
func (t *Token) get(token string) bool {
	tt := etcd.EtcdPathJoin([]string{tokenKeyBase, token})
	uid, err := etcd.Client.GetKV(tt)
	if err != nil {
		log.Critical(err)
		return false
	}
	t.Token = token
	t.UID = uid
	t.EtcdKey = tt
	t.Expirytime = time.Now().Unix() + int64(tokenExpire)
	return true
}

//GetByUser get token by user
func (t *Token) getByUser(u *User) bool {
	tokenList := etcd.Client.ListDir(tokenKeyBase)
	for _, tk := range tokenList {
		uid, err := etcd.Client.GetKV(tk)
		if err != nil {
			return false
		}
		if uid == u.ID {
			token := strings.TrimPrefix(tk, tokenKeyBase+etcd.EtcdSep)
			t.EtcdKey = tk
			t.Token = token
			t.UID = u.ID
			t.Role = u.Role
			t.Expirytime = time.Now().Unix() + int64(tokenExpire)
			return true
		}
	}
	return false
}

//Save save token to etcd
func (t *Token) save() error {
	err := etcd.Client.SetKVWithTTL(t.EtcdKey, t.UID, tokenExpire)
	if err != nil {
		log.Error(fmt.Sprintf("save token %s to etcd failed! %s", t.EtcdKey, err.Error()))
	}
	return err
}

//Update update token ttl
func (t *Token) update() error {
	err := etcd.Client.UpdateTTL(t.EtcdKey, tokenExpire)
	return err
}

//Remove remove token from etcd
func (t *Token) remove() error {
	err := etcd.Client.RemoveKey(t.EtcdKey)
	return err
}
