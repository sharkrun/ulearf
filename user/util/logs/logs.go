package logs

import (
	"fmt"
	"github.com/astaxie/beego"
	ufleetSystem "go-ufleetutil/system"
	"strings"
)

func Debug(v ...interface{}) {
	beego.Debug(v...)
}

func Info(v ...interface{}) {
	beego.Info(v...)
}

func Warn(v ...interface{}) {
	beego.Warn(v...)
}

func Warning(v ...interface{}) {
	beego.Warning(v...)
}

func Error(v ...interface{}) {
	beego.Error(v...)
}

func Critical(v ...interface{}) {
	beego.Critical(v...)
}

func Logetcd(level int, operator, operate string, v ...interface{}) {
	auditClient := ufleetSystem.NewAuditClient()
	switch level {
	case 1:
		auditClient.Level = "Critical"
	case 2:
		auditClient.Level = "Error"
	case 3:
		auditClient.Level = "Warning"
	case 4:
		auditClient.Level = "Info"
	case 5:
		auditClient.Level = "Debug"
	default:
		auditClient.Level = "Debug"
	}

	n := len(v)
	auditClient.Object = fmt.Sprintf(strings.Repeat("%v", n), v...)
	auditClient.Operator = operator
	auditClient.Operate = operate
	auditClient.Module = "user"

	beego.Info("[", operator, "]", "[", operate, "]", auditClient.Object)
	err := auditClient.Create()
	if err != nil {
		Error(err)
	}
}
