package broadcast

import (
	//"log"
	"encoding/json"
	"fmt"
	"os"
	"time"
	"ufleet/user/util/logs"
	"ufleet/user/util/request"
)

var (
	storeModule   = "STORE_HOST"
	clusterModule = "CLUSTER_HOST"
)

type BroadCast struct {
	Module string            `json:"module"`
	Method string            `json:"method"`
	Path   string            `json:"path"`
	Header map[string]string `json:"header"`
	Data   map[string]string `json:"data"`
}

func (b *BroadCast) SetDaTa(key, value string) {
	if b.Data == nil {
		b.Data = make(map[string]string, 0)
	}
	b.Data[key] = value
}

func (b *BroadCast) SetHeader(key, value string) {
	if b.Header == nil {
		b.Header = make(map[string]string, 0)
	}
	b.Header[key] = value
}

func (b *BroadCast) Call() (string, error) {
	url, err := b.getServerUrl()
	if err != nil {
		logs.Info("Get[", b.Module, "]url fail,as [", err.Error(), "]")
		return "", err
	}

	url = url + b.Path

	json_data, err := json.Marshal(b.Data)
	if err != nil {
		logs.Info("Parse[", b.Module, "]data fail,as [", err.Error(), "]")
		return "", err
	}

	ret_json_str, err := request.MakeRequest(url, b.Method, b.Header, string(json_data))
	if err != nil {
		logs.Info("call[", url, "]return [", err.Error(), "]")
	}
	return ret_json_str, err
}

func (b *BroadCast) getServerUrl() (string, error) {
	endpoint := os.Getenv(b.Module)
	if len(endpoint) > 0 {
		logs.Info("Server[", b.Module, "]url is [", endpoint, "]")
		return endpoint, nil
	}
	return "", fmt.Errorf("Server [%s] invalid.", b.Module)
}

func DeleteGroup(token string, group string) {
	notifyList := make([]*BroadCast, 0)

	gcast := BroadCast{}
	gcast.Method = "POST"
	gcast.Module = storeModule
	gcast.Path = "/v1/store/deletegroup"
	gcast.SetHeader("token", token)
	gcast.SetDaTa("group", group)
	notifyList = append(notifyList, &gcast)

	ccast := BroadCast{}
	ccast.Method = "POST"
	ccast.Module = clusterModule
	ccast.Path = "/v1/cluster/deletegroup"
	ccast.SetHeader("token", token)
	ccast.SetDaTa("group", group)
	notifyList = append(notifyList, &ccast)

	go SentMessage(notifyList, 3)
}

func SentMessage(notifyList []*BroadCast, tryNum int) {
	for _, bcast := range notifyList {
		for i := 0; i < tryNum; i++ {
			_, err := bcast.Call()
			if err == nil {
				break
			} else {
				time.Sleep(time.Duration(5) * time.Second)
			}
		}
	}
}
