package main

import "fmt"

type User struct {
    Name string
}

func (u *User) Greet() {
    fmt.Println("Hello " + u.Name)
}

func main() {
    u := User{Name: "Alice"}
    u.Greet()
}
