package repository

import (
	"encoding/json"
	"errors"
	"path/filepath"
	"time"

	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

//InitRegistry init registry module
func InitRepository() {
	etcd.Client.MakeDir(repositoryKeyBase)
}

// Exist check if this repository exists in specificate group store
func (r *Repository) exist(user_id string) bool {
	repositoryList := etcd.Client.ListDir(etcd.EtcdPathJoin([]string{repositoryKeyBase, user_id}))
	for _, k := range repositoryList {
		if filepath.Base(k) == r.ID {
			return true
		}
	}
	return false
}

// Exist check if this registry exists in specificate group store
func (r *Repository) repeat(user_id string, address string) bool {
	repoList := GetUserRepository(user_id)
	for _, k := range repoList {
		if r.ID == k.ID {
			continue
		}
		if address == k.Address {
			return true
		}
	}
	return false
}

//Get get user repository info by id
func (r *Repository) Get(user_id string, id string) error {
	key := etcd.EtcdPathJoin([]string{repositoryKeyBase, user_id, id})
	info, err := etcd.Client.GetKV(key)
	if err != nil {
		log.Critical(err)
		return errors.New("repository not exists")
	}
	repo := &Repository{}
	err = json.Unmarshal([]byte(info), repo)
	if err != nil {
		log.Critical(err)
		return errors.New("repository data error")
	}
	repo.ID = id
	*r = *repo
	return nil
}

// Save save repository to store
func (r *Repository) save(user_id string) error {
	r.UpdateTime = int(time.Now().Unix())

	k := etcd.EtcdPathJoin([]string{repositoryKeyBase, user_id, r.ID})
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

// Delete delete repository from store
func (r *Repository) delete(user_id string) error {
	k := etcd.EtcdPathJoin([]string{repositoryKeyBase, user_id, r.ID})
	err := etcd.Client.RemoveKey(k)
	if err != nil {
		log.Critical(err)
		return err
	}
	return nil
}

// Delete delete user all repository from store
func (r *Repository) RemoveUserRepo(user_id string) error {
	k := etcd.EtcdPathJoin([]string{repositoryKeyBase, user_id})
	err := etcd.Client.RemoveDir(k)
	if err != nil {
		log.Critical(err)
		return err
	}
	return nil
}

// Add add repository to store, will check existing
func (r *Repository) Add(user_id string) error {
	if r.repeat(user_id, r.Address) {
		log.Critical("The repository address repeat")
		return errors.New("repository address repeat")
	}

	r.ID = etcd.Client.GenerateId("Repo")
	return r.save(user_id)
}

// Update update repository in store, will check existing
func (r *Repository) Update(user_id string, repo *Repository) error {
	if r.repeat(user_id, repo.Address) {
		log.Critical("The repository address repeat")
		return errors.New("repository address repeat")
	}

	if repo.Name != "" {
		r.Name = repo.Name
	}

	if repo.Address != "" {
		r.Address = repo.Address
	}

	if repo.Token != "" {
		r.Token = repo.Token
	}

	if repo.Type != "" {
		r.Type = repo.Type
	}

	return r.save(user_id)
}

// Remove remove repository in store, will check existing
func (r *Repository) Remove(user_id string) error {
	if r.exist(user_id) == false {
		return errors.New("no repository")
	}
	return r.delete(user_id)
}

// GetAllRepository return all user data
func GetAllRepository() []Repository {
	repositoryList := []Repository{}

	// Get all group repository
	keys := etcd.Client.ListDir(repositoryKeyBase)
	for _, key := range keys {
		user_id := filepath.Base(key)
		repositoryList = append(repositoryList, GetUserRepository(user_id)...)
	}

	return repositoryList
}

//GetUserRepository get user repository from store
func GetUserRepository(user_id string) []Repository {
	repositoryList := []Repository{}
	keys := etcd.Client.ListDir(etcd.EtcdPathJoin([]string{repositoryKeyBase, user_id}))
	for _, key := range keys {
		repositoryInfo, err := etcd.Client.GetKV(key)
		if err != nil {
			log.Critical(err)
			continue
		}
		repository := Repository{}
		err = json.Unmarshal([]byte(repositoryInfo), &repository)
		if err != nil {
			log.Critical(err)
			continue
		}
		repositoryList = append(repositoryList, repository)
	}
	return repositoryList
}
