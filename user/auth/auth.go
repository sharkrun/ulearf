package auth

import (
	"encoding/json"
	"github.com/astaxie/beego"
	"log"
	"time"

	etcd "ufleet/user/util/etcdclientv3"
)

const (
	//AUTH_TYPE_LOCAL indicate to use local user for auth
	AUTH_TYPE_LOCAL = "local"
	//AUTH_TYPE_LDAP indicate to use ldap user for auth
	AUTH_TYPE_LDAP = "ldap"
)

var (
	//AuthConfig to record system auth config in mem
	authConfig SystemAuthConfig
	expirytime = int64(0)

	etcdKeyBase = beego.AppConfig.String("etcdbase")
	//AuthConfigKey for etcd key of auth config
	AuthConfigKey = etcd.EtcdPathJoin([]string{etcdKeyBase, beego.AppConfig.String("etcdsystemconfig"), "auth", "config"})
)

//SystemAuthConfig record system auth type
type SystemAuthConfig struct {
	Type string `json:"type"`
}

//InitAuth init auth module
func InitAuth() {
	config, err := LoadAuthConfig()
	if err != nil {
		authConfig.Type = AUTH_TYPE_LOCAL
		SaveAuthConfig()
	} else {
		authConfig = *config
	}


}

func ReloadAuthInfo() *SystemAuthConfig {
	if expirytime <= time.Now().Unix() {
		config, err := LoadAuthConfig()
		if err != nil {
			return &authConfig
		} else {
			authConfig = *config
			expirytime = time.Now().Unix() + 10
		}
	}

	return &authConfig
}

//LoadAuthConfig read auth config from etcd
func LoadAuthConfig() (*SystemAuthConfig, error) {
	authconfigstr, err := etcd.Client.GetKV(AuthConfigKey)
	if err != nil {
		return nil, err
	}
	config := new(SystemAuthConfig)
	err = json.Unmarshal([]byte(authconfigstr), config)
	if err != nil {
		log.Println(err)
		return nil, err
	}
	return config, nil
}

//SaveAuthConfig save auth config in etcd
func SaveAuthConfig() error {
	configstr, err := json.Marshal(authConfig)
	if err != nil {
		log.Println(err)
		return err
	}
	err = etcd.Client.SetKV(AuthConfigKey, string(configstr))
	if err != nil {
		log.Println(err)
		return err
	}
	return nil
}

//SetAuthType to set auth type to required
func SetAuthType(authType string) {
	authConfig.Type = authType
	SaveAuthConfig()
}

//GetAuthType to get auth type
func GetAuthType() string {
	config := ReloadAuthInfo()
	return config.Type
}
