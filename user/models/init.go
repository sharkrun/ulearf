package models

import (
	"time"
	//"log"

	"os"
	ability "ufleet/user/ability"
	auth "ufleet/user/auth"
	"ufleet/user/license"
	node "ufleet/user/node"
	registry "ufleet/user/registry"
	repository "ufleet/user/repository"
	role "ufleet/user/role"
	user "ufleet/user/user"
	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

func InitModels() {
	initEtcdClient()
	initHeartBeat()
	initAuth()
	initUser()
	initRole()
	initRegistry()
	InitRepository()
	initLicense()
	//initAbility()
	//initRoleAbility()

}

func initEtcdClient() {
	etcdCluster, found := os.LookupEnv("ETCDCLUSTER")
	if !found {
		panic("env valude ETCDCLUSTER should be set")
	} else {
		if etcdCluster == "" {
			panic("env valude ETCDCLUSTER should not be empty")
		}
	}

	if err := etcd.InitClient(etcdCluster); err != nil {
		log.Critical("ETCD connect fail")
	}
	for {
		ret := etcd.Client.TestClient()
		if ret == true {
			log.Info("ETCD auto test ok")
			break
		}
		log.Critical("ETCD auto test fail, please check the config")
		time.Sleep(3 * time.Second)
	}
}

func initUser() {
	user.InitUser()
}

func initAuth() {
	auth.InitAuth()
	auth.InitLdap()
}

func initRole() {
	role.InitRole()
}

func initAbility() {
	go func() {
		for {
			ability.InitAbility()
			time.Sleep(30 * time.Second)
			log.Info("Init Ability")
		}
	}()

}

func initRoleAbility() {
	go func() {
		for {
			ability.InitRoleAbility()
			time.Sleep(30 * time.Second)
			log.Info("Init Role Ability")
		}
	}()
}

func initRegistry() {
	registry.InitRegistry()
}

func InitRepository() {
	repository.InitRepository()
}

func initHeartBeat() {
	node.InitNode()
}

func initLicense() {
	license.InitDefaultLicense()
}
