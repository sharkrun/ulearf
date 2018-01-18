package ability

import (
	"io/ioutil"
	"os"
	"path/filepath"
)

func ReadAbilityListFromFile(filepath string) ([]*Ability, error) {
	dat, err := ioutil.ReadFile(filepath)
	if err != nil {
		return []*Ability{}, err
	}
	list, err2 := AbilityListFromJson(string(dat))
	if err2 != nil {
		return []*Ability{}, err2
	}
	return list, nil
}

func FileExists(name string) bool {
	if _, err := os.Stat(name); err != nil {
		if os.IsNotExist(err) {
			return false
		}
	}
	return true
}

func GetAbilityFilePath() string {
	var err error
	var appPath, workPath, appConfigPath string
	appPath, err = filepath.Abs(filepath.Dir(os.Args[0]))
	if err != nil {
		return ""
	}
	workPath, err = os.Getwd()
	if err != nil {
		return ""
	}
	appConfigPath = filepath.Join(workPath, "conf", "userability.json")
	if !FileExists(appConfigPath) {
		appConfigPath = filepath.Join(appPath, "conf", "userability.json")
		if !FileExists(appConfigPath) {
			return ""
		}
	}
	return appConfigPath
}

func ReadRoleAbilityListFromFile(filepath string) ([]*RoleAbility, error) {
	dat, err := ioutil.ReadFile(filepath)
	if err != nil {
		return []*RoleAbility{}, err
	}
	list, err2 := RoleAbilityListFromJson(string(dat))
	if err2 != nil {
		return []*RoleAbility{}, err2
	}
	return list, nil
}

func GetRoleAbilityFilePath() string {
	var err error
	var appPath, workPath, appConfigPath string
	appPath, err = filepath.Abs(filepath.Dir(os.Args[0]))
	if err != nil {
		return ""
	}
	workPath, err = os.Getwd()
	if err != nil {
		return ""
	}
	appConfigPath = filepath.Join(workPath, "conf", "userability-init.json")
	if !FileExists(appConfigPath) {
		appConfigPath = filepath.Join(appPath, "conf", "userability-init.json")
		if !FileExists(appConfigPath) {
			return ""
		}
	}
	return appConfigPath
}
