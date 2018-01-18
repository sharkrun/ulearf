package models

type ErrorMsg struct {
	StatusCode int    `json:"error_code"`
	Message    string `json:"error_msg"`
}

type ResponseMsg struct {
	StatusCode int    `json:"error_code"`
	Message    string `json:"error_msg"`
}

func GenerateErrorMsg(status int, msg string) *ErrorMsg {
	var emsg ErrorMsg
	emsg.StatusCode = status
	emsg.Message = msg
	return &emsg
}

func GenerateResponseMsg(msg string) *ResponseMsg {
	var rmsg ResponseMsg
	rmsg.StatusCode = 0
	rmsg.Message = msg
	return &rmsg
}
