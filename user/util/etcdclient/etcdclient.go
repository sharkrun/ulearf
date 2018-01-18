package etcdclient

import (
	//"log"
	"fmt"
	"github.com/coreos/etcd/client"
	"golang.org/x/net/context"
	"strings"
	"time"
	"ufleet/user/util/stringid"

	log "ufleet/user/util/logs"
)

type EtcdClient struct {
	Endpoints      string
	TimeoutSeconds int
	kvapi          client.KeysAPI
}

var (
	EtcdSep = "/"
	Client  = &EtcdClient{}
)

func (c *EtcdClient) InitClient(endpoints string, timeout int) {
	log.Info("Init etcd client:", endpoints)
	etcdEndpoints := strings.Split(endpoints, ",")
	cfg := client.Config{
		Endpoints:               etcdEndpoints,
		Transport:               client.DefaultTransport,
		HeaderTimeoutPerRequest: time.Second * time.Duration(timeout),
	}
	cl, err := client.New(cfg)
	if err != nil {
		log.Critical(err)
		panic("etcd client generate fail")
	}
	c.Endpoints = endpoints
	c.TimeoutSeconds = timeout
	c.kvapi = client.NewKeysAPI(cl)
}

func (c *EtcdClient) TestClient() bool {
	_, e := c.GetKV("/")
	if e != nil {
		return false
	}
	return true
}

func (c *EtcdClient) SetKV(k string, v string) error {
	_, err := c.kvapi.Set(context.Background(), k, v, nil)
	if err != nil {
		log.Critical(err)
		return err
	}

	return err
}

func (c *EtcdClient) SetKVWithTTL(k string, v string, second int) error {
	var opts client.SetOptions
	opts.TTL = time.Duration(int64(second) * int64(time.Second))
	_, err := c.kvapi.Set(context.Background(), k, v, &opts)
	if err != nil {
		log.Critical(err)
		return err
	}

	return err
}

func (c *EtcdClient) UpdateTTL(k string, second int) error {
	var opts client.SetOptions
	opts.TTL = time.Duration(int64(second) * int64(time.Second))
	opts.Refresh = true
	_, err := c.kvapi.Set(context.Background(), k, "", &opts)
	if err != nil {
		log.Critical(err)
		return err
	}

	return err
}

func (c *EtcdClient) GetKV(k string) (string, error) {
	resp, err := c.kvapi.Get(context.Background(), k, nil)
	if err != nil {
		// log.Critical(err)
		return "", err
	}
	log.Debug("etcd get key:", k, " value:", resp.Node.Value)
	return resp.Node.Value, nil
}

func (c *EtcdClient) MakeDir(k string) error {
	log.Debug("etcd make dir use key:", k)
	var opts client.SetOptions
	opts.Dir = true
	_, err := c.kvapi.Set(context.Background(), k, "", &opts)
	if err != nil {
		log.Critical(err)
		return err
	}
	return err
}

func (c *EtcdClient) ListDir(k string) []string {
	log.Debug("etcd list dir use key:", k)
	resp, err := c.kvapi.Get(context.Background(), k, nil)
	if err != nil {
		log.Critical(err)
		return []string{}
	}
	if resp.Node.Dir == false {
		return []string{}
	}

	var keylist []string
	for _, node := range resp.Node.Nodes {
		keylist = append(keylist, node.Key)
	}
	log.Debug("etcd list dir use key:", k, " get list", keylist)
	return keylist
}

func (c *EtcdClient) RemoveKey(k string) error {
	_, err := c.kvapi.Delete(context.Background(), k, nil)
	if err != nil {
		log.Critical(err)
		return err
	}
	return err
}

func (c *EtcdClient) RemoveDir(k string) error {
	var opts *client.DeleteOptions
	opts = new(client.DeleteOptions)
	opts.Dir = true
	opts.Recursive = true
	_, err := c.kvapi.Delete(context.Background(), k, opts)
	if err != nil {
		log.Critical(err)
		return err
	}
	return err
}

func (c *EtcdClient) Watcher(k string, recursive bool) client.Watcher {
	var opts = new(client.WatcherOptions)
	opts.Recursive = recursive
	watcher := c.kvapi.Watcher(k, opts)
	return watcher
}

func EtcdPathJoin(keylist []string) string {
	return strings.Join(keylist, EtcdSep)
}

// EtcdSet save data in etcd
func (c *EtcdClient) EtcdSet(key string, value string, dir bool) error {
	_, err := c.kvapi.Set(context.Background(), key, value, &client.SetOptions{Dir: dir})
	if err != nil {
		return err
	}
	return nil
}

// EtcdGet get key from etcd
func (c *EtcdClient) EtcdGet(key string) (*client.Response, error) {
	resp, err := c.kvapi.Get(context.Background(), key, nil)
	if err != nil {
		return nil, err
	}
	return resp, nil
}

// EtcdUpdate update specfic key's value
func (c *EtcdClient) EtcdUpdate(key string, value string) error {
	_, err := c.kvapi.Update(context.Background(), key, value)
	if err != nil {
		return err
	}
	return nil
}

// EtcdDelete delete a key from etcd
func (c *EtcdClient) EtcdDelete(key string, dir bool) error {
	_, err := c.kvapi.Delete(
		context.Background(),
		key,
		&client.DeleteOptions{Dir: dir, Recursive: true},
	)
	if err != nil {
		return err
	}
	return nil
}

// EtcdKeyCheck check if key exist in etcd
func (c *EtcdClient) EtcdKeyCheck(key string) (bool, error) {
	_, err := c.EtcdGet(key)
	if err != nil {
		return false, err
	}
	return true, nil
}

// EtcdKeyCheck check if key exist in etcd
func (c *EtcdClient) GenerateId(prefix string) string {
	return fmt.Sprintf("%s%s%s", prefix, time.Now().Format("20060102150405"), stringid.GetRandomString(4))
}
