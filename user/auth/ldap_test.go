package auth

import (
	"testing"
)

func initTestLdapConfig() *SystemLdapConfig {
	config := new(SystemLdapConfig)
	InitLdapConfig(config)
	config.Host = "192.168.3.231"
	config.BindDN = "cn=admin,dc=testldap,dc=com"
	config.BindPassword = "alfred"
	config.UserBase = "ou=testou2,dc=testldap,dc=com"
	config.Filter = "(uid=%s)"
	//config.UserDN = "uid=%s,ou=testou2,dc=testldap,dc=com"
	config.UseBindDN = true
	return config
}

func TestLdapVerify(t *testing.T) {
	config := initTestLdapConfig()
	LdapConfig = config
	testuser := "alfred21"
	testpwdt := "alfred21"
	testpwdf := "123456"
	_, ok := LdapVerify(testuser, testpwdt)
	if ok == false {
		t.Error("should verify ok")
	}
	_, ok = LdapVerify(testuser, testpwdf)
	if ok == true {
		t.Error("should verify fail")
	}
}

func TestLdapUserList(t *testing.T) {
	config := initTestLdapConfig()
	LdapConfig = config

	userlist, err := LdapListUser()
	if err != nil {
		t.Error("List user fail ", err)
	}
	if len(userlist) == 0 {
		t.Error("List user empty ")
	}
	t.Log(userlist)
}

func TestLdapUserGet(t *testing.T) {
	config := initTestLdapConfig()
	LdapConfig = config
	testuser := "alfred21"
	testuserf := "alfredfff"
	user, ok := LdapGetUser(testuser)
	if ok == false {
		t.Error("should get ok")
	}
	t.Log(user)
	_, ok = LdapGetUser(testuserf)
	if ok == true {
		t.Error("should get fail")
	}
}
