
package p

class A { fun m(x: Int): Int = x + 1 }
fun f(): Int = A().m(1)
