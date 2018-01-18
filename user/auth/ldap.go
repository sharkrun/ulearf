package auth

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"github.com/astaxie/beego"
	"github.com/gogits/gogs/modules/auth/ldap"
	ld "gopkg.in/ldap.v2"
	"strings"
	"time"

	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

var (
	//LdapKey for etcd key of ldap config
	LdapKey = etcd.EtcdPathJoin([]string{etcdKeyBase, beego.AppConfig.String("etcdsystemconfig"), "auth", "ldap"})
	//LdapConfig to record ldap config in mem
	ldapConfig     = new(SystemLdapConfig)
	ldapexpirytime = int64(0)
)

//SystemLdapConfig for ldap config
type SystemLdapConfig struct {
	Host              string `json:"host"`         // LDAP host
	Port              int    `json:"port"`         // port number, always set to 389
	SecurityProtocol  int    `json:"security"`     // set 0 to use no security protocol, 1 for LDAPS, 2 for TLS
	SkipVerify        bool   `json:"skipVerfiy"`   // set false to skip verify
	BindDN            string `json:"bindDN"`       // DN to bind with, means admin name, like 'cn=admin,dc=testldap,dc=com'
	BindPassword      string `json:"bindPassword"` // Bind DN password, means admin password
	UserBase          string `json:"userBase"`     // Base search path for users
	UserDN            string `json:"userDN"`       // Template for the DN of the user for simple auth
	AttributeUsername string `json:"attrUsername"` // Username attribute, always set to uid
	AttributeName     string `json:"attrName"`     // First name attribute, always set to givenName
	AttributeSurname  string `json:"attrSurName"`  // Surname attribute, always set to sn
	AttributeMail     string `json:"attrEmail"`    // E-mail attribute, always set to mail
	AttributesInBind  bool   `json:"attrInBind"`   // fetch attributes in bind context (not user)
	Filter            string `json:"filter"`       // Query filter to validate entry, search filter, like '(uid=%s)'
	AdminFilter       string `json:"adminFileter"` // Query filter to check if user is admin
	UseBindDN         bool   `json:"useBindDN"`    // set to true to use admin to login and user UserBase and Filter to search user
}

//LdapVerifyData user info to verify password in ldap
type LdapVerifyData struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

//LdapVerifyResult verify result of ldap verify
type LdapVerifyResult struct {
	Result bool `json:"result"`
}

//LdapUser user info get from ldap server
type LdapUser struct {
	Username   string `json:"username"`
	Name       string `json:"nickname"`
	Email      string `json:"email"`
	IsAdmin    bool   `json:"isadmin"`
	IsInSystem bool   `json:"isInSystem"`
}

//LdapUser user info and group
type LdapUserData struct {
	Users []LdapUser `json:"users,omitempty"`
	Group []string   `json:"group,omitempty"`
}

//InitLdap init ldap module
func InitLdap() {
	if config, err := loadLdapConfig(); err != nil {
		ldapConfig = InitLdapConfig()
		SaveLdapConfig(ldapConfig)
	} else {
		ldapConfig = config
	}
}

//InitLdapConfig set default value for ldap config
func InitLdapConfig() *SystemLdapConfig {
	config := new(SystemLdapConfig)
	config.SecurityProtocol = 0
	config.SkipVerify = false
	config.Port = 389
	config.AttributeMail = "mail"
	config.AttributeUsername = "uid"
	config.AttributeSurname = "sn"
	config.AttributeName = "givenName"
	config.UseBindDN = true
	config.Filter = "(uid=%s)"
	return config
}

//SaveLdapConfig save ldap config to etcd
func SaveLdapConfig(config *SystemLdapConfig) error {
	configstr, err := json.Marshal(config)
	if err != nil {
		log.Info(err)
		return err
	}
	err = etcd.Client.SetKV(LdapKey, string(configstr))
	if err != nil {
		log.Info(err)
	} else {
		ldapexpirytime = 0
	}

	return err
}

func ReloadLdapConfig() *SystemLdapConfig {
	if ldapexpirytime <= time.Now().Unix() {
		config, err := loadLdapConfig()
		if err != nil {
			return ldapConfig
		} else {
			ldapConfig = config
			ldapexpirytime = time.Now().Unix() + 10
		}
	}

	return ldapConfig
}

//LoadLdapConfig load ldap config from etcd
func loadLdapConfig() (*SystemLdapConfig, error) {
	configstr, err := etcd.Client.GetKV(LdapKey)
	if err != nil {
		log.Info(err)
		return nil, err
	}
	config := new(SystemLdapConfig)
	err = json.Unmarshal([]byte(configstr), config)
	if err != nil {
		log.Info(err)
		return nil, err
	}
	return config, nil
}

func ClearCache() {
	ldapexpirytime = 0
}

func sourceLoad() *ldap.Source {
	var source = new(ldap.Source)

	config := ReloadLdapConfig()

	source.Host = config.Host
	source.Port = config.Port
	source.SecurityProtocol = ldap.SecurityProtocol(config.SecurityProtocol)
	source.SkipVerify = config.SkipVerify
	source.BindDN = config.BindDN
	source.BindPassword = config.BindPassword
	source.UserBase = config.UserBase
	source.UserDN = config.UserDN
	source.AttributeUsername = config.AttributeUsername
	source.AttributeName = config.AttributeName
	source.AttributeSurname = config.AttributeSurname
	source.AttributeMail = config.AttributeMail
	source.AttributesInBind = config.AttributesInBind
	source.Filter = config.Filter
	source.AdminFilter = config.AdminFilter
	return source
}

//LdapVerify verify user name and password through ldap server
func LdapVerify(name, password string) (*LdapUser, bool) {
	var source = sourceLoad()
	var username, firstname, surname, mail string
	var isadmin, ok bool
	username, firstname, surname, mail, isadmin, ok = source.SearchEntry(name, password, !ldapConfig.UseBindDN)
	user := new(LdapUser)
	user.Username = username
	user.Name = firstname + " " + surname
	user.Email = mail
	user.IsAdmin = isadmin
	return user, ok
}

//LdapGetUser get ldap user from ldap server by username
func LdapGetUser(name string) (*LdapUser, bool) {
	var source = sourceLoad()
	var username, firstname, surname, mail string
	var isadmin bool
	l, err := dial(source)
	if err != nil {
		log.Error("LDAP Connect error ", source.Host, " error ", err)
		return nil, false
	}
	defer l.Close()

	err = l.Bind(source.BindDN, source.BindPassword)
	if err != nil {
		log.Critical(err)
		return nil, false
	}

	badCharacters := "\x00()*\\"
	if strings.ContainsAny(name, badCharacters) {
		log.Debug(fmt.Printf("'%s' contains invalid query characters. Aborting.", name))
		return nil, false
	}
	userFilter := fmt.Sprintf(source.Filter, name)

	search := ld.NewSearchRequest(
		source.UserBase,
		ld.ScopeWholeSubtree, ld.NeverDerefAliases, 0, 0, false,
		userFilter,
		[]string{source.AttributeUsername, source.AttributeName, source.AttributeSurname, source.AttributeMail},
		nil)

	sr, err := l.Search(search)
	if err != nil {
		log.Error("LDAP Search failed unexpectedly! ", err)
		return nil, false
	} else if len(sr.Entries) != 1 {
		log.Error("LDAP Search failed unexpectedly! search result count:", len(sr.Entries))
		return nil, false
	}

	username = sr.Entries[0].GetAttributeValue(source.AttributeUsername)
	firstname = sr.Entries[0].GetAttributeValue(source.AttributeName)
	surname = sr.Entries[0].GetAttributeValue(source.AttributeSurname)
	mail = sr.Entries[0].GetAttributeValue(source.AttributeMail)

	if len(source.AdminFilter) > 0 {
		search = ld.NewSearchRequest(
			source.UserBase,
			ld.ScopeWholeSubtree, ld.NeverDerefAliases, 0, 0, false,
			source.AdminFilter,
			[]string{source.AttributeUsername},
			nil)

		sr, err = l.Search(search)
		if err != nil {
			log.Error("LDAP Admin Search failed unexpectedly!", err)
		} else if len(sr.Entries) < 1 {
			log.Error("LDAP Admin Search failed")
		} else {
			isadmin = true
		}
	}
	user := new(LdapUser)
	user.Username = username
	user.Name = firstname + " " + surname
	user.Email = mail
	user.IsAdmin = isadmin
	return user, true
}

func dial(ls *ldap.Source) (*ld.Conn, error) {
	tlsCfg := &tls.Config{
		ServerName:         ls.Host,
		InsecureSkipVerify: ls.SkipVerify,
	}
	if ls.SecurityProtocol == ldap.SECURITY_PROTOCOL_LDAPS {
		return ld.DialTLS("tcp", fmt.Sprintf("%s:%d", ls.Host, ls.Port), tlsCfg)
	}

	conn, err := ld.Dial("tcp", fmt.Sprintf("%s:%d", ls.Host, ls.Port))
	if err != nil {
		return nil, fmt.Errorf("Dial: %v", err)
	}

	if ls.SecurityProtocol == ldap.SECURITY_PROTOCOL_START_TLS {
		if err = conn.StartTLS(tlsCfg); err != nil {
			conn.Close()
			return nil, fmt.Errorf("StartTLS: %v", err)
		}
	}

	return conn, nil
}

//LdapListUser get user list from ldap server
func LdapListUser() ([]*LdapUser, error) {
	var source = sourceLoad()
	var userlist = make([]*LdapUser, 0)
	l, err := dial(source)
	if err != nil {
		log.Critical(err)
		return userlist, err
	}
	defer l.Close()
	err = l.Bind(source.BindDN, source.BindPassword)
	if err != nil {
		log.Critical(err)
		return userlist, err
	}
	userFilter := "(uid=*)"
	search := ld.NewSearchRequest(
		source.UserBase,
		ld.ScopeWholeSubtree, ld.NeverDerefAliases,
		0, 0, false, userFilter,
		[]string{source.AttributeUsername, source.AttributeName, source.AttributeSurname, source.AttributeMail},
		nil)

	sr, err := l.Search(search)
	if err != nil {
		log.Critical(err)
		return userlist, err
	}
	for _, entry := range sr.Entries {
		username := entry.GetAttributeValue(source.AttributeUsername)
		user, ok := LdapGetUser(username)
		if ok == true {
			userlist = append(userlist, user)
		}
	}
	return userlist, nil
}
