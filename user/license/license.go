package license

import (
	"encoding/json"
	"errors"
	"github.com/astaxie/beego"
	"sync"
	"time"
	etcd "ufleet/user/util/etcdclientv3"
	log "ufleet/user/util/logs"
)

var (
	etcdKeyBase    = beego.AppConfig.String("etcdbase")
	licenseKeyBase = etcd.EtcdPathJoin([]string{etcdKeyBase, "license"})
	defaultLicense = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlpXSFg6TUdSSjpaUjdZOjRMWFg6WlBLNjpVTDY3OkRJQTM6NDRBNDpOTUhROkNVVVY6RUtPVTpOTFhGIn0.eyJhY2Nlc3MiOnt9LCJqdGkiOiI2NDQ0ODcxNzk2NjczMDQxMzEyIiwic3ViIjoiVUZsZWV0IiwiZXhwIjoxNTM5NjUwNjkzLCJpc3MiOiJ5b3VydW5jbG91ZCIsImlhdCI6MTUwODExNDY5MywibmJmIjoxNTA4MTE0NjkyLCJhdWQiOiJFdmVyeSBPbmUifQ.MlmgBKxvJ2k_QjqwuQsbx-12PhgkLjiIviCQF6RavhSqdobRjxrvwFheseiJzXDNCWI2RFRHZFCNA4NBz0vjO93ifiS55h6GO2DQ3wO_FzFX-VGSHyLs3gY8fmXwSqWQZbhNYx1FfVOcRvrSvMDM7j75XxDowQTSno6qU1mTMYpx3UBP4VJWQLbhqWhSm7fuKytkCYwsTp21j8REviFvR1188fg6u0TfSlZ9iAxuQsSBJNADo2cQqiIjS_NQ-eliXxlHUJytnFRD7F2oQR6DvEDFq5L7ZC09Gm-ykZ8MJamClKaXzVC-p0_omn_yne0MKKtHUvj3xMHw9oyfVI3erg"
	ticker         = time.Tick(5 * time.Minute)
	mu             = sync.Mutex{}
)

var globalLicenseInfo *LicenseInfo = nil

type LicenseInfo struct {
	Group      int    `json:"group"`
	User       int    `json:"user"`
	Storage    string `json:"storage"`
	Issuer     string `json:"issuer"`
	Subject    string `json:"subject"`
	Audience   string `json:"audience"`
	Expiration int64  `json:"expiration"`
	NotBefore  int64  `json:"notBefore"`
	IssuedAt   int64  `json:"issuedAt"`
	JWTID      string `json:"jti"`
	ActiveTime int64  `json:"activeTime"`
}

type License struct {
	Certificate string `json:"certificate"`
	UpdateTime  int    `json:"updateTime"`
}

func loopLoad() {
	for {
		select {
		case <-ticker:
			syncWithEtcd()
		}
	}
}

func syncWithEtcd() error {
	mu.Lock()
	globalLicenseInfo = nil
	mu.Unlock()

	data, err := etcd.Client.GetKV(licenseKeyBase)
	if err != nil {
		log.Error(err)
		return errors.New("license not exists")
	}
	license := new(License)
	err = json.Unmarshal([]byte(data), license)
	if err != nil {
		log.Error(err)
		return errors.New("license data error")
	}

	if license.Certificate == "" {
		log.Error("GetLicenseInfo fail,as[license not exist]")
		return errors.New("license not exist.")
	}

	token, err := NewToken(license.Certificate)
	if err != nil {
		log.Error("GetLicenseInfo NewToken fail,as[", err.Error(), "]")
		return errors.New("license invalid.")
	}

	verifyOpts, err := LoadPublicKey()
	if err != nil {
		log.Error("GetLicenseInfo LoadPublicKey fail,as[", err.Error(), "]")
		return errors.New("public key invalid.")
	}

	if err = token.Verify(*verifyOpts); err != nil {
		log.Error("GetLicenseInfo Verify fail,as[", err.Error(), "]")
		return errors.New("license token verify invalid.")
	}

	info := genLicenseInfoFromToken(token)
	// 证书激活时间
	info.ActiveTime = int64(license.UpdateTime)

	updateCacheLicenseInfo(info)
	return nil
}

func updateCacheLicenseInfo(info *LicenseInfo) error {
	if info == nil {
		return errors.New("updateCacheLicenseInfo: invalid info")
	}
	mu.Lock()
	defer mu.Unlock()
	globalLicenseInfo = info
	return nil
}

//Get license info
func (r *License) get() error {
	info, err := etcd.Client.GetKV(licenseKeyBase)
	if err != nil {
		log.Error(err)
		return errors.New("license not exists")
	}
	license := &License{}
	err = json.Unmarshal([]byte(info), license)
	if err != nil {
		log.Error(err)
		return errors.New("license data error")
	}
	*r = *license
	return nil
}

// Save license to store
func (r *License) save() error {
	r.UpdateTime = int(time.Now().Unix())

	v, err := json.Marshal(r)
	if err != nil {
		log.Error(err)
		return err
	}
	err = etcd.Client.SetKV(licenseKeyBase, string(v))
	if err != nil {
		log.Error(err)
		return err
	}
	return nil
}

// Delete delete license from store
func (r *License) delete() error {
	err := etcd.Client.RemoveKey(licenseKeyBase)
	if err != nil {
		log.Error(err)
		return err
	}
	return nil
}

// Update license in store
func (r *License) update(certificate string) error {
	r.Certificate = certificate
	return r.save()
}

func genLicenseInfoFromToken(token *Token) *LicenseInfo {
	info := new(LicenseInfo)
	info.Issuer = token.Claims.Issuer
	info.Subject = token.Claims.Subject
	info.Audience = token.Claims.Audience
	info.Expiration = token.Claims.Expiration
	info.NotBefore = token.Claims.NotBefore
	info.IssuedAt = token.Claims.IssuedAt
	info.JWTID = token.Claims.JWTID
	return info
}

//Get license info
func GetLicenseInfo() (*LicenseInfo, error) {
	if globalLicenseInfo == nil {
		return nil, errors.New("license invalid")
	}
	return globalLicenseInfo, nil
}

func UpdateLicenseInfo(certificate string) error {
	token, err := NewToken(certificate)
	if err != nil {
		log.Error("UpdateLicenseInfo NewToken fail,as[", err.Error(), "]")
		return errors.New("license invalid.")
	}

	verifyOpts, err := LoadPublicKey()
	if err != nil {
		log.Error("UpdateLicenseInfo LoadPublicKey fail,as[", err.Error(), "]")
		return errors.New("public key invalid.")
	}

	if err = token.Verify(*verifyOpts); err != nil {
		log.Error("UpdateLicenseInfo Verify fail,as[", err.Error(), "]")
		return errors.New("license invalid.")
	}

	li := License{}
	err = li.update(certificate)
	if err != nil {
		log.Error("UpdateLicenseInfo Update fail,as[", err.Error(), "]")
		return err
	}
	info := genLicenseInfoFromToken(token)
	//证书激活时间
	info.ActiveTime = int64(li.UpdateTime)

	updateCacheLicenseInfo(info)
	return nil
}

func InitDefaultLicense() {
	// try to load license from etcd
	// if not exist, then try to init default license
	syncWithEtcd()
	if globalLicenseInfo == nil {
		err := UpdateLicenseInfo(defaultLicense)
		if err != nil {
			log.Error("init default license failed as [", err.Error(), "]")
		} else {
			log.Info("init default license success!")
		}
	}

	// keep sync with etcd
	go loopLoad()
}
