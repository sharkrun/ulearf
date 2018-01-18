package protocol

type BaseError struct {
	Errs      error
	StatusDtl StatusDetail
}

func (b *BaseError) Error() string {
	return "错误详情:" + b.Errs.Error()
}

type StatusDetail struct {
	Code string
	Desc string
}