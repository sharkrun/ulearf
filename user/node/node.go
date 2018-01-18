package node

import (
	"crypto/rand"
	"encoding/json"
	"github.com/astaxie/beego"
	"math/big"
	"os"
	"time"
	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

var (
	myid          = os.Getenv("UFLEET_NODE_ID")
	ticket        = int64(0)
	interval      = int64(6)
	rate          = int64(1)
	lasttime      = time.Now().Unix()
	masterid      = "-"
	etcdKeyBase   = beego.AppConfig.String("etcdbase")
	masterKeyPath = etcd.EtcdPathJoin([]string{etcdKeyBase, "master"})
)

//Token record user login token
type MasterInfo struct {
	ID     string `json:"id"`
	Ticket int64  `json:"ticket"`
}

//InitUser to init user module, read etcd and try set default admin
func InitNode() {
	if len(myid) > 0 {
		log.Info("InitNode success, The node id is[" + myid + "]")
		go heartbeat()
	} else {
		log.Critical("InitNode fail, The node id is empty.")
	}
}

func heartbeat() {
	for {
		update_ticket()
		time.Sleep(time.Duration(interval*rate) * time.Second)
	}
}

func update_ticket() bool {

	masterInfo, err := etcd.Client.GetKV(masterKeyPath)
	if err != nil {
		log.Critical("read master info fail.")
		SetMaster()
		rate = 1
		return true
	} else {
		log.Debug("read master info success, info=[" + masterInfo + "]")
	}

	master := MasterInfo{}
	err = json.Unmarshal([]byte(masterInfo), &master)
	if err != nil {
		log.Critical("Unmarshal master info fail.")
		SetMaster()
		rate = 1
		return true
	}

	if master.ID == myid {
		rate = 1
		master.Ticket += interval
		err = SaveMasterInfo(&master)
		if err == nil {
			ticket = master.Ticket + int64(1)
		} else {
			log.Critical("save master info fail.")
		}
	} else if master.Ticket < ticket {
		master.ID = myid
		master.Ticket = ticket + ramdom()

		err = SaveMasterInfo(&master)
		if err == nil {
			rate = 1
			ticket = master.Ticket + int64(1)
		} else {
			rate = 2
			log.Critical("save master info fail.")
		}
	} else {
		rate = 2
		log.Debug("master id=[" + master.ID + "]")
		masterid = master.ID
		ticket = master.Ticket + int64(1)
	}
	return true

}

func is_master() bool {
	return myid == masterid
}

func SetMaster() error {
	master := MasterInfo{myid, ticket + ramdom()}
	return SaveMasterInfo(&master)
}

func ramdom() int64 {
	return RandInt64(100, 1000)
}

func RandInt64(min, max int64) int64 {
	maxBigInt := big.NewInt(max)
	i, _ := rand.Int(rand.Reader, maxBigInt)
	if i.Int64() < min {
		return RandInt64(min, max)
	}
	return i.Int64()
}

//Save master info to etcd
func SaveMasterInfo(master *MasterInfo) error {
	v, err := json.Marshal(master)
	if err != nil {
		log.Critical(err)
		return err
	}
	err = etcd.Client.SetKV(masterKeyPath, string(v))
	if err != nil {
		log.Critical(err)
		return err
	}
	log.Debug("save master info success, info=[" + string(v) + "]")
	return nil
}
