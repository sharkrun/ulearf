package ability

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestUserAbilityListFromFile(t *testing.T) {
	workPath, err := os.Getwd()
	if err != nil {
		t.Error("get wd failed:", err)
	}
	appConfigPath := filepath.Join(workPath, "..", "conf", "userability.json")

	t.Log("ability json file:", appConfigPath)
	list, err := ReadAbilityListFromFile(appConfigPath)
	if err != nil {
		t.Error("read ability from file fail:", err)
	}
	t.Log("read list:", list)
}
