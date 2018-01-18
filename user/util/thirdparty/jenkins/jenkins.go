package jenkins

import (
	"ufleet/user/util/request"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

var (
	jenkinsHost string
)

func CreateCredential(userName string, password string, token string) (string, error) {
	headers := make(map[string]string)
	headers["token"] = token

	param := struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}{
		Username: userName,
		Password: password,
	}

	parambytes, err := json.Marshal(param)
	if err != nil {
		return "", fmt.Errorf("jenkins create Credentials fail for : %v", err)
	}

	url := jenkinsHost + "/v1/pipeline_api/credentials"
	respString, err := request.MakeRequest(url, "POST", headers, string(parambytes))
	if err != nil {
		return "", err
	}

	id := struct {
		ID string `json:"id"`
	}{}

	err = json.Unmarshal([]byte(respString), &id)
	if err != nil {
		return "", fmt.Errorf("unmarshal jenkins resp data fail for %v", err)
	}

	return id.ID, nil
}

func DeleteCredential(id string, token string) error {

	headers := make(map[string]string)
	headers["token"] = token
	url := jenkinsHost + "/v1/pipeline_api/credentials/" + id

	_, err := request.MakeRequest(url, "DELETE", headers, "")
	if err != nil {
		return err
	}

	return nil
}

func init() {

	jenkinsHost = os.Getenv("JENKINSHOST")
	if len(strings.TrimSpace(jenkinsHost)) == 0 {
		jenkinsHost = "localhost:8080"
	}

}
