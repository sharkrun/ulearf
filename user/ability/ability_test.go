package ability

import (
	"testing"
)

func TestAbilityToJson(t *testing.T) {
	var abi *Ability = new(Ability)
	abi.Object = "user"
	abi.Operate = []string{"create", "get", "update", "delete"}
	abi_str, err := abi.ToJSON()
	if err != nil || len(abi_str) == 0 {
		t.Error("ability to json fail:", abi)
	}
}

func TestAbilityEqual(t *testing.T) {
	var a, b, c, d *Ability
	a = new(Ability)
	b = new(Ability)
	c = new(Ability)
	d = new(Ability)
	a.Object = "user"
	a.Operate = []string{"create", "get", "update"}
	b.Object = "user"
	b.Operate = []string{"update", "create", "get"}
	c.Object = "user"
	c.Operate = []string{"update", "create"}
	d.Object = "role"
	d.Operate = []string{"update", "create", "get"}
	if a.Equal(b) == false {
		t.Error("ability equal error, should equal:", a, b)
		t.FailNow()
	}
	if a.Equal(c) == true {
		t.Error("ability equal error, should not equal 1:", a, c)
		t.FailNow()
	}
	if a.Equal(d) == true {
		t.Error("ability equal error, should not equal 2:", a, d)
		t.FailNow()
	}
}

func TestAbilityFromJson(t *testing.T) {
	var ts string = `{"object":"user","operate":["create","get","update","delete"]}`
	var ts2 string = `{"object":"user","operate":[{"ablity":["create","get","update","delete"]}]}`
	var abi *Ability = new(Ability)
	abi.Object = "user"
	abi.Operate = []string{"create", "get", "update", "delete"}
	abi_str, err := abi.ToJSON()

	var abi2 *Ability = new(Ability)
	err = abi2.FromJson(abi_str)
	if err != nil {
		t.Error("ability from json error:", err.Error())

	}
	if abi.Equal(abi2) == false {
		t.Error("ability from json not match:", abi, abi2)
		t.FailNow()
	}

	var abi3 *Ability = new(Ability)
	err = abi3.FromJson(ts)
	if err != nil {
		t.Error("ability from json error:", err.Error())
		t.FailNow()
	}
	if abi.Equal(abi3) == false {
		t.Error("ability from json not match:", abi, abi3)
		t.FailNow()
	}

	var abi4 *Ability = new(Ability)
	err = abi4.FromJson(ts2)
	t.Log("error should not nil:", err)
	if err == nil {
		t.Error("ability from json should error:", ts2)
		t.FailNow()
	}

}

func TestListToJson(t *testing.T) {
	var l []*Ability
	var a *Ability = new(Ability)
	var b *Ability = new(Ability)
	a.Object = "user"
	a.Operate = []string{"get", "update"}
	b.Object = "role"
	b.Operate = []string{"get", "modify"}
	l = append(l, a, b)
	l_str, err := AbilityListToJson(l)
	if err != nil || len(l_str) == 0 {
		t.Error("list to json fail", l, err)
		t.FailNow()
	}
}

func TestListFromJson(t *testing.T) {
	var l []*Ability
	var a *Ability = new(Ability)
	var b *Ability = new(Ability)
	a.Object = "user"
	a.Operate = []string{"get", "update"}
	b.Object = "role"
	b.Operate = []string{"get", "modify"}
	l = append(l, a, b)
	l_str, err := AbilityListToJson(l)
	if err != nil || len(l_str) == 0 {
		t.Error("list to json fail", l, err)
		t.FailNow()
	}

	var r []*Ability
	r, err2 := AbilityListFromJson(l_str)
	if err2 != nil {
		t.Error("list to json fail", l_str, err2)
		t.FailNow()
	}
	for _, ri := range r {
		if ri.Object == a.Object {
			if a.Equal(ri) == false {
				t.Error("json to ability not equal ,fail", a, ri)
			}
		}
		if ri.Object == b.Object {
			if b.Equal(ri) == false {
				t.Error("json to ability not equal ,fail", b, ri)
			}
		}
	}
}
