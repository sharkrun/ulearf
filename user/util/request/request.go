package request

import (
	"fmt"
	"io/ioutil"
	"net/http"
	"strings"
)

var httpClient *http.Client = &http.Client{}

func MakeRequest(url string, method string, headers map[string]string, json_data string) (string, error) {
	var req *http.Request
	var err error
	client := httpClient
	req, err = http.NewRequest(method, url, nil)
	if len(json_data) > 0 {
		req, err = http.NewRequest(method, url, strings.NewReader(json_data))
	}
	if err != nil {
		return "", err
	}
	req.Header.Set("Accept", "application/json")
	for k, v := range headers {
		req.Header.Add(k, v)
	}

	resp, errd := client.Do(req)
	if errd != nil {
		return "", errd
	}
	defer resp.Body.Close()
	if resp.StatusCode/100 != 2 {
		return "", fmt.Errorf("HTTP Error,url:%s,method:%s,status code:%d", url, method, resp.StatusCode)
	}
	body, errr := ioutil.ReadAll(resp.Body)
	if errr != nil {
		return "", errr
	}
	return string(body), nil
}
