package models

import "encoding/json"

// Lightweight representation of event
type MockEvent struct {
	ProcessName string     `json:"ProcessName"`
	EventName   string     `json:"eventName"`
	UserId      int        `json:"userId"`
	Args        []Argument `json:"args"`
}

type Argument struct {
	Name        string      `json:"name"`
	Type        string      `json:"type"`
	RawValue    interface{} `json:"value"`
	StringValue *string
	IntValue    *int
}

func (a *Argument) UnmarshalJSON(data []byte) error {
	type _Argument Argument
	var temp struct {
		RawValue json.RawMessage `json:"value"`
		_Argument
	}
	if err := json.Unmarshal(data, &temp); err != nil {
		return err
	}
	*a = Argument(temp._Argument)

	switch temp.Type {
	case "const char*":
		var strVal string
		if err := json.Unmarshal([]byte(temp.RawValue), &strVal); err != nil {
			return err
		}
		a.StringValue = &strVal
	}
	return nil
}

type EventCounter map[string]int
