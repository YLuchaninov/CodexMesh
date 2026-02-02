
import Foundation

final class A { func m(_ x: Int) -> Int { x + 1 } }
func f() -> Int { A().m(1) }
