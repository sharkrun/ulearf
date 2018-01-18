package protocol

/*
错误码分段信息
0001 --- 1000 	应用栈
1001 --- 2000   服务
2001 --- 3000   容器
3001 --- 4000   主机
4001 --- 5000   集群
5001 --- 5500   镜像
5501 --- 6000   环境
6001 --- 7000   用户和权限
7001 --- 8000   容器日志和命令行
9000 --- 10000  其他
*/

var (
	C_SUCCESS = StatusDetail{"0000", "成功"}

	C_LOGIN_FAIL_COUNT_LIMIT   = StatusDetail{"6001", "连续登录错误次数过多，账号被锁定，请联系管理员解锁或稍后重试"}
	C_AUTH_TYPE_UNKNOWN        = StatusDetail{"6002", "未知的校验类型"}
	C_SYSTEMPROFILE_INVALID    = StatusDetail{"6003", "非法用户"}
	C_INACTIVE_USER            = StatusDetail{"6004", "未激活用户"}
	C_USERNAME_OR_PASSWD_ERROR = StatusDetail{"6005", "用户名或密码错误"}
	C_USERNAME_NOT_EXIST       = StatusDetail{"6006", "用户不存在"}
	C_USER_NO_GROUP            = StatusDetail{"6007", "用户不属于任何用户组"}
)
