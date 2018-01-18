package registry

import (
	"encoding/base64"
	"encoding/json"
	"errors"
	"path/filepath"
	"time"
	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

//InitRegistry init registry module
func InitRegistry() {
	etcd.Client.MakeDir(registryKeyBase)
}

// Exist check if this registry exists in specificate group store
func (r *Registry) exist(group string) bool {
	registryList := etcd.Client.ListDir(etcd.EtcdPathJoin([]string{registryKeyBase, group}))
	for _, k := range registryList {
		if filepath.Base(k) == r.ID {
			return true
		}
	}
	return false
}

// Exist check if this registry exists in specificate group store
func (r *Registry) repeat(group, address, name string) bool {
	registryList := GetGroupRegistry(group)
	for _, k := range registryList {
		if r.ID == k.ID {
			continue
		}
		if address == k.Address {
			return true
		}
		if name == k.Name {
			return true
		}
	}
	return false
}

//Get get user registry info by id
func (r *Registry) Get(group string, id string) error {
	key := etcd.EtcdPathJoin([]string{registryKeyBase, group, id})
	info, err := etcd.Client.GetKV(key)
	if err != nil {
		log.Critical(err)
		return errors.New("registry not exists")
	}
	reg := &Registry{}
	err = json.Unmarshal([]byte(info), reg)
	if err != nil {
		log.Critical(err)
		return errors.New("registry data error")
	}
	reg.ID = id
	*r = *reg
	return nil
}

// Save save registry to store
func (r *Registry) save(group string) error {
	r.UpdateTime = int(time.Now().Unix())

	k := etcd.EtcdPathJoin([]string{registryKeyBase, group, r.ID})
	v, err := json.Marshal(r)
	if err != nil {
		log.Critical(err)
		return err
	}
	err = etcd.Client.SetKV(k, string(v))
	if err != nil {
		log.Critical(err)
		return err
	}
	return nil
}

// Delete delete registry from store
func (r *Registry) delete(group string) error {
	k := etcd.EtcdPathJoin([]string{registryKeyBase, group, r.ID})
	err := etcd.Client.RemoveKey(k)
	if err != nil {
		log.Critical(err)
		return err
	}
	return nil
}

// Delete delete group all registry from store
func (r *Registry) RemoveGroupReg(group string) error {
	k := etcd.EtcdPathJoin([]string{registryKeyBase, group})
	err := etcd.Client.RemoveDir(k)
	if err != nil {
		log.Critical(err)
		return err
	}
	return nil
}

// Add add registry to store, will check existing
func (r *Registry) Add(group string) error {
	if r.repeat(group, r.Address, r.Name) {
		log.Critical("The Registry address repeat")
		return errors.New("The Registry address repeat")
	}

	r.ID = etcd.Client.GenerateId("Reg")
	r.Belong = group
	r.Password = base64.StdEncoding.EncodeToString([]byte(r.Password))

	return r.save(group)
}

// Update update registry in store, will check existing
func (r *Registry) Update(group string, reg *Registry) error {
	if r.repeat(group, reg.Address, reg.Name) {
		log.Critical("The Registry address repeat")
		return errors.New("The Registry address repeat")
	}

	if reg.Name != "" {
		r.Name = reg.Name
	}

	if reg.Address != "" {
		r.Address = reg.Address
	}

	if reg.User != "" {
		r.User = reg.User
	}

	if reg.Password != "" {
		r.Password = base64.StdEncoding.EncodeToString([]byte(reg.Password))
	}

	if reg.Email != "" {
		r.Email = reg.Email
	}

	if reg.Extend != "" {
		r.Extend = reg.Extend
	}

	return r.save(group)
}

// Remove remove registry in store, will check existing
func (r *Registry) Remove(group string) error {
	if r.exist(group) == false {
		return errors.New("no registry")
	}
	return r.delete(group)
}

// GetAllRegistry return all user data
func GetAllRegistry() []Registry {
	registryList := []Registry{}

	// Get all group registry
	keys := etcd.Client.ListDir(registryKeyBase)
	for _, key := range keys {
		group := filepath.Base(key)
		registryList = append(registryList, GetGroupRegistry(group)...)
	}

	return registryList
}

//GetUserRegistry get user registry from store
func GetGroupRegistry(group string) []Registry {
	registryList := []Registry{}
	keys := etcd.Client.ListDir(etcd.EtcdPathJoin([]string{registryKeyBase, group}))
	for _, key := range keys {
		registryInfo, err := etcd.Client.GetKV(key)
		if err != nil {
			log.Critical(err)
			continue
		}
		registry := Registry{}
		err = json.Unmarshal([]byte(registryInfo), &registry)
		if err != nil {
			log.Critical(err)
			continue
		}
		registryList = append(registryList, registry)
	}
	return registryList
}

func CountByGroup(group string) int {
	keys := etcd.Client.ListDir(etcd.EtcdPathJoin([]string{registryKeyBase, group}))
	return len(keys)
}

func CountTotal() int {
	total := 0
	keys := etcd.Client.ListDir(registryKeyBase)
	for _, key := range keys {
		total += CountByGroup(filepath.Base(key))
	}
	return total
}
