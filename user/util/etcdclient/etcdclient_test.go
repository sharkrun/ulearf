package etcdclient

import (
	//"errors"
	//"os"
	"path/filepath"
	//"strings"
	"testing"
	"time"

	"golang.org/x/net/context"
)

var (
	endpoints      = "http://127.0.0.1:2379"  //需为真实存在的etcd服务器地址
	fake_endpoints = "http://127.0.0.1:12379" //需为非真实存在的etcd服务器地址
)

func TestTestClient(t *testing.T) {
	var client = &EtcdClient{}
	client.InitClient(endpoints, 5)
	b := client.TestClient()
	if b == false {
		t.Error("TestClient failed, should success")
	}

	var fake_client = &EtcdClient{}
	fake_client.InitClient(fake_endpoints, 5)
	f := fake_client.TestClient()
	if f == true {
		t.Error("TestClient success, should fail")
	}
}

func TestSetKVandGetKV(t *testing.T) {
	var client = &EtcdClient{}
	client.InitClient(endpoints, 5)

	var k = "/Test/TestSetKVandGetKV"
	var v = "TestSetKVandGetKV"
	err := client.SetKV(k, v)
	if err != nil {
		t.Error("SetKV fail:", err)
	}
	gv, err1 := client.GetKV(k)
	if err1 != nil {
		t.Error("GetKV fail:", err1)
	}
	if gv != v {
		t.Error("GetKV data error:", v, gv)
	}
	client.RemoveKey(k)
}

func TestSetKVWithTTL(t *testing.T) {
	var client = &EtcdClient{}
	client.InitClient(endpoints, 5)

	var k = "/Test/TestSetKVWithTTL"
	var v = "TestSetKVWithTTL"
	err := client.SetKVWithTTL(k, v, 3)
	if err != nil {
		t.Error("SetKVWithTTL fail:", err)
	}
	gv, err1 := client.GetKV(k)
	if err1 != nil {
		t.Error("GetKV fail:", err1)
	}
	if gv != v {
		t.Error("GetKV data error:", v, gv)
	}
	time.Sleep(time.Second * 4)
	_, err2 := client.GetKV(k)
	if err2 != nil {
		t.Log("GetKV fail:", err2)
	}

}

func TestMakeDirAndListDir(t *testing.T) {
	var client = &EtcdClient{}
	client.InitClient(endpoints, 5)

	var k = "/Test/TestMakeDirandListDir"
	var dirlist = []string{"dir1", "dir2", "dir3"}
	var err error
	for _, dir := range dirlist {
		dirk := EtcdPathJoin([]string{k, dir})
		t.Log("Makedir:", dirk)
		err = client.MakeDir(dirk)
		if err != nil {
			t.Error("MakeDir fail:", err)
		}
	}
	var find bool = false
	getlist := client.ListDir(k)
	for _, getdir := range getlist {
		find = false
		getb := filepath.Base(getdir)
		for _, dir := range dirlist {
			if dir == getb {
				find = true
			}
		}
		if find == false {
			t.Error("Dir ", getb, "not find in ListDir", getlist)
		}
	}
	client.RemoveDir(k)
}

func TestWatch(t *testing.T) {
	var client = &EtcdClient{}
	client.InitClient(endpoints, 5)

	var k = "/Test/TestWatch"
	var dirlist = []string{"dir1", "dir2", "dir3"}
	var err error
	go func() {
		watcher := client.Watcher(k, true)
		for {
			resp, err := watcher.Next(context.Background())
			if err != nil {
				t.Error(err)
			}
			t.Log(resp)
			if resp.Action == "set" || resp.Action == "delete" {
				actk := resp.Node.Key
				actkb := filepath.Base(actk)
				find := false
				for _, dir := range dirlist {
					if dir == actkb {
						find = true
					}
				}
				if find == false {
					t.Error("Act Dir ", actkb, "not find in ListDir", dirlist)
				}
			}
		}
	}()
	for _, dir := range dirlist {
		dirk := EtcdPathJoin([]string{k, dir})
		t.Log("Makedir:", dirk)
		err = client.MakeDir(dirk)
		if err != nil {
			t.Error("MakeDir fail:", err)
		}
	}
	for _, dir := range dirlist {
		dirk := EtcdPathJoin([]string{k, dir})
		t.Log("Removedir:", dirk)
		err = client.RemoveDir(dirk)
		if err != nil {
			t.Error("MakeDir fail:", err)
		}
	}
	client.RemoveDir(k)
}
