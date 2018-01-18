package etcdclientv3

import (
	"errors"
	"fmt"
	"github.com/coreos/etcd/clientv3"
	"golang.org/x/net/context"
	"strings"
	"time"
	//log "ufleet/user/util/logs"
	"path/filepath"
	"ufleet/user/util/stringid"
)

var (
	EtcdSep = "/"
	Client  = &EtcdClient{}
)

type EtcdClient struct {
	endpoints   []string
	dialTimeout int
	RawClient   *clientv3.Client
}

func InitClient(etcdcluster string) error {
	endpoints := strings.Split(etcdcluster, ",")
	c := &EtcdClient{
		endpoints,
		5,
		nil,
	}

	cli, err := clientv3.New(clientv3.Config{
		Endpoints:   endpoints,
		DialTimeout: 5 * time.Second,
	})
	if err != nil {
		return err
	}
	c.RawClient = cli
	Client = c
	return nil
}

func (c *EtcdClient) TestClient() bool {
	_, err := c.RawClient.Get(context.Background(), "/")
	if err != nil {
		return false
	}
	return true
}

func (c *EtcdClient) SetKV(k string, v string) error {
	_, err := c.RawClient.Put(context.Background(), k, v)
	if err != nil {
		//log.Critical(err)
		return err
	}

	return err
}

func (c *EtcdClient) SetKVWithTTL(k string, v string, second int) error {
	leaseResp, err := c.RawClient.Grant(context.TODO(), int64(second))
	if err != nil {
		return err
	}
	_, err = c.RawClient.Put(context.TODO(), k, v, clientv3.WithLease(leaseResp.ID))
	if err != nil {
		//log.Critical(err)
		return err
	}
	return err
}

func (c *EtcdClient) UpdateTTL(k string, second int) error {
	// retrive old data
	getresp, err := c.RawClient.Get(context.Background(), k)
	if err != nil {
		return err
	}

	//delete old data
	_, err = c.RawClient.Delete(context.Background(), k)
	if err != nil {
		return err
	}

	// set key value with new lease
	leaseResp, err := c.RawClient.Grant(context.TODO(), int64(second))
	if err != nil {
		return err
	}
	for _, ev := range getresp.Kvs {
		_, err = c.RawClient.Put(context.TODO(), string(ev.Key), string(ev.Value), clientv3.WithLease(leaseResp.ID))
		if err != nil {
			//log.Critical(err)
			return err
		}
	}

	return err
}

func (c *EtcdClient) GetKV(k string) (string, error) {
	getresp, err := c.RawClient.Get(context.Background(), k)
	if err != nil {
		return "", err
	}
	for _, ev := range getresp.Kvs {
		return string(ev.Value), nil
	}
	return "", errors.New("key not exist")
}

func (c *EtcdClient) MakeDir(k string) error {
	//log.Debug("etcd make dir use key:", k)
	_, err := c.RawClient.Put(context.Background(), k, "")
	if err != nil {
		//log.Critical(err)
		return err
	}
	return err
}

func (c *EtcdClient) ListDir(k string) []string {
	result := make([]string, 0)
	resp, err := c.RawClient.Get(context.Background(), k, clientv3.WithPrefix())
	if err != nil {
		return result
	}

	// 父级目录
	basedir := filepath.Base(k)

	// 父目录下的一级子目录
	collector := make(map[string]bool)
	for _, ev := range resp.Kvs {
		dirs := strings.Split(string(ev.Key), EtcdSep)
		for i, dir := range dirs {
			if dir == basedir && i+1 < len(dirs) {
				collector[EtcdPathJoin(dirs[0:i+2])] = true
				break
			}
		}
	}
	for k, _ := range collector {
		result = append(result, k)
	}
	return result
}

func (c *EtcdClient) RemoveDir(k string) error {
	_, err := c.RawClient.Delete(context.Background(), k, clientv3.WithPrefix())
	if err != nil {
		return err
	}
	return err
}

func (c *EtcdClient) RemoveKey(k string) error {
	_, err := c.RawClient.Delete(context.Background(), k)
	if err != nil {
		return err
	}
	return err
}

func EtcdPathJoin(keylist []string) string {
	return strings.Join(keylist, EtcdSep)
}

// EtcdKeyCheck check if key exist in etcd
func (c *EtcdClient) GenerateId(prefix string) string {
	return fmt.Sprintf("%s%s%s", prefix, time.Now().Format("20060102150405"), stringid.GetRandomString(4))
}
