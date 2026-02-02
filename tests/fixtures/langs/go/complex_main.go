package main

import (
	"fmt"
	"math"
)

// Logger is a simple interface
type Logger interface {
	Log(msg string)
}

// MyService with a method
type MyService struct {
	Prefix string
}

/*
Log implementation for MyService.
Testing multiline block comments.
*/
func (s *MyService) Log(msg string) {
	fmt.Printf("[%s] %s\n", s.Prefix, msg)
}

// Compute handles some math
func Compute(val float64) float64 {
	return math.Sqrt(val)
}

func main() {
	svc := &MyService{Prefix: "DEBUG"}
	svc.Log("Starting...")
	fmt.Println(Compute(16))
}
