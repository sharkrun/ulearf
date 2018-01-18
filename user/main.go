package main

import (
	"github.com/astaxie/beego"
	"os"
	"os/signal"
	"syscall"
	"ufleet/user/user"

	"github.com/astaxie/beego/logs"
	"ufleet/user/models"
	_ "ufleet/user/routers"
	log "ufleet/user/util/logs"
)

func main() {
	beego.BConfig.WebConfig.DirectoryIndex = true
	beego.BConfig.WebConfig.StaticDir["/swagger"] = "swagger"

	beego.SetLevel(beego.LevelInformational)
	beego.SetLogFuncCall(false)
	logs.SetLogger(logs.AdapterFile, `{"filename":"./log/user.log","perm":"0664"}`)

	OSEnvSet()
	models.InitModels()

	go LogTrap()

	beego.Run()
}

func OSEnvSet() {
	log.Info("ENV:", os.Environ())

	etcdEndpoints := os.Getenv("ETCDCLUSTER")
	if len(etcdEndpoints) > 0 {
		log.Info("Recv etcd endpoints from env:", etcdEndpoints)
		err := beego.AppConfig.Set("etcdendpoints", etcdEndpoints)
		if err != nil {
			log.Warning("Set etcd endpoint to appconfig fail", err)
		}
	}
}

func LogTrap() {
	c := make(chan os.Signal, 1)
	signals := []os.Signal{syscall.SIGUSR1, syscall.SIGUSR2}
	signal.Notify(c, signals...)
	go func() {
		for sig := range c {
			go func(sig os.Signal) {
				switch sig {
				case syscall.SIGUSR1:
					user.ResetAdminPass()
				case syscall.SIGUSR2:
					beego.SetLevel(beego.LevelDebug)
				}
			}(sig)
		}
	}()
}
