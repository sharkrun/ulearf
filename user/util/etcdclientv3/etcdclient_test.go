package etcdclientv3

import (
	"go-ethereum/log"
	"testing"
	"time"
)

var (
	valid_addr   = "http://192.168.8.65:2379"
	invalid_addr = "http://99.99.0.1:2389"
)

func TestConnect(t *testing.T) {
	err := InitClient(valid_addr)
	if err != nil {
		t.Error("init etcd3 client failed")
	}

	err = InitClient(invalid_addr)
	if err != nil {
		t.Log("TestConnect ok")
	}
}

func TestTestClient(t *testing.T) {
	ok := Client.TestClient()
	if ok {
		t.Log("TestClient ok")
	} else {
		t.Error("TestClient fail")
	}
}

func TestSetKv(t *testing.T) {
	err := Client.SetKV("aaa", "bbb")
	if err != nil {
		t.Error("TestSetKv fail")
	} else {
		t.Log("TestSetKv ok")
	}
}

func TestGet(t *testing.T) {
	res, err := Client.GetKV("aaa")
	if err != nil {
		t.Error("TestGet fail")
	} else {
		if res != "bbb" {
			t.Error("TestGet resp data error")
		} else {
			t.Log("TestGet ok")
		}
	}
}

func TestSetKVWithTTL(t *testing.T) {
	err := Client.SetKVWithTTL("ccc", "ddd", 5)
	if err != nil {
		t.Error("TestSetKVWithTTL fail")
	} else {
		t.Log("TestSetKVWithTTL ok")
	}
	time.Sleep(5 * time.Second)

	data, err := Client.GetKV("ccc")
	if data == "ddd" {
		log.Error("TestSetKVWithTTL lease error, the key should be deleted")
	}
}

func TestUpdateTTL(t *testing.T) {
	err := Client.SetKVWithTTL("eee", "fff", 5)
	if err != nil {
		t.Error("TestSetKVWithTTL fail")
	} else {
		t.Log("TestSetKVWithTTL ok")
	}
	time.Sleep(2 * time.Second)

	Client.UpdateTTL("eee", 5)

	time.Sleep(2 * time.Second)
	data, err := Client.GetKV("eee")
	if data != "fff" {
		log.Error("TestSetKVWithTTL update lease error the key should be there")
	}
}

func TestRemoveKey(t *testing.T) {
	err := Client.RemoveKey("aaa")
	if err != nil {
		t.Error("TestRemoveKey fail")
	}

	data, _ := Client.GetKV("aaa")
	if data == "bbb" {
		t.Error("TestRemoveKey fail, key still exist")
	} else {
		t.Log("TestRemoveKey ok")
	}
}

func TestMkdir(t *testing.T) {
	err := Client.MakeDir("testdir")
	if err != nil {
		t.Error("TestMkdir fail")
	} else {
		t.Log("TestMkdir ok")
	}
}

func TestListDir(t *testing.T) {
	Client.SetKV("1/2/3", "ddddddddddddd")
	Client.SetKV("1/3/4", "ddddddddddddd")
	Client.SetKV("1/5/8", "ddddddddddddd")
	dirs := Client.ListDir("1")
	t.Log("dirs: ", dirs)

	// 2 is the only subdir of 1
	if len(dirs) != 3 {
		t.Error("TestListDir fail", dirs)
	} else {
		t.Log("TestListDir ok")
	}
}
