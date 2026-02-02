
pub struct A;
impl A { pub fn m(&self, x: i32) -> i32 { x + 1 } }
pub fn f() -> i32 { A.m(1) }
