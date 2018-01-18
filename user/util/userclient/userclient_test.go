package userclient

import (
	"encoding/json"
	"fmt"
	//"net/http"
	//"strings"
	"math/rand"
	"strconv"
	"testing"
	"time"

	"ufleet/user/user"
)

var endpoint = "http://127.0.0.1:8881"

func SuperadminLogin(endpoint string) (token, id string) {
	name := "superadmin"
	password := "superadmin"
	url := "/v1/user/login"
	login_info := new(user.UserLogin)
	login_info.Username = name
	login_info.Password = password
	p_json, err1 := json.Marshal(login_info)
	if err1 != nil {
		return "", ""
	}
	body, err2 := MakeRequest(endpoint+url, "POST", nil, string(p_json))
	if err2 != nil {
		return "", ""
	}
	token_s := new(user.Token)
	err3 := json.Unmarshal([]byte(body), token_s)
	if err3 != nil {
		return "", ""
	}
	return token_s.Token, token_s.Uid
}

func UserCreateForTest(username, endpoint string) (id string) {
	addu := new(user.User)
	addu.Username = username
	addu.Password = username
	addu.Profile.Email = username + "@test.com"
	addu.Profile.Nickname = "nickname_" + username
	url := "/v1/user/"
	p_json, err1 := json.Marshal(addu)
	if err1 != nil {
		fmt.Println("User Create data prepare fail:", err1)
		return ""
	}
	token, _ := SuperadminLogin(endpoint)
	if len(token) == 0 {
		fmt.Println("Superadmin login fail")
		return ""
	}
	headers := make(map[string]string)
	headers["Token"] = token
	body, err2 := MakeRequest(endpoint+url, "POST", headers, string(p_json))
	if err2 != nil {
		fmt.Println("User Create Request fail:", err2)
		return ""
	}
	ret := new(user.User)
	err3 := json.Unmarshal([]byte(body), ret)
	if err3 != nil {
		fmt.Println("User Create data get fail:", err3)
		return ""
	}
	return ret.Id
}

func UserDeleteForTest(id, endpoint string) error {
	url := "/v1/user/" + id

	token, _ := SuperadminLogin(endpoint)
	if len(token) == 0 {
		return fmt.Errorf("Superadmin login fail")
	}

	headers := make(map[string]string)
	headers["Token"] = token

	_, err2 := MakeRequest(endpoint+url, "DELETE", headers, "")
	if err2 != nil {
		return err2
	}
	return nil
}

func TestUserVerifyAndGet(t *testing.T) {
	var token string
	token = "12345678901234567890"
	t.Logf("Unkown login token:%s", token)
	u, err := UserVerifyAndGet(token, endpoint)
	if err == nil {
		t.Errorf("User Verify Error, token %s should not exist.", token)
	}

	token, _ = SuperadminLogin(endpoint)
	t.Logf("Superadmin login token:%s", token)
	u, err = UserVerifyAndGet(token, endpoint)
	if err != nil {
		fmt.Println(err)
		t.Errorf("User Verify Error, token %s should exist.", token)
	}
	if u == nil {
		t.Errorf("User Verify Error, User should exist.")
	}
}

func TestUserGetById(t *testing.T) {
	var token, id_err, id_su string

	token, id_su = SuperadminLogin(endpoint)

	id_err = "12345678901234567890"
	t.Logf("INFO:Unkown user id:%s", id_err)
	u, err := UserGetById(id_err, token, endpoint)
	if err == nil {
		t.Errorf("User Get Error, user id %s should not exist.", id_err)
	} else {
		t.Logf("Get unkown user OK.")
	}

	t.Logf("INFO:Superadmin user id:%s", id_su)
	u, err = UserGetById(id_su, token, endpoint)
	if err != nil {
		fmt.Println(err)
		t.Errorf("User Get Error, user id %s should exist.", id_su)
	} else {
		t.Logf("Get Superadmin %s OK")
	}
	if u == nil {
		t.Errorf("User Get Error, User should exist.")
	}
}

func TestUserCreateAndDelete(t *testing.T) {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	username := "test_user_" + strconv.Itoa(r.Intn(10000))

	id := UserCreateForTest(username, endpoint)
	t.Logf("create return id:%s", id)
	if len(id) == 0 {
		t.Errorf("Add User %s fail.", username)
		t.FailNow()
	} else {
		t.Logf("Add User %s OK.", username)
	}

	err := UserDeleteForTest(id, endpoint)
	if err != nil {
		t.Errorf("Delete Error:%s", err.Error())
	} else {
		t.Logf("Delete User %s OK.", username)
	}

}
