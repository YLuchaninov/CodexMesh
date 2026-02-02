
#include <iostream>

struct A { int m(int x){ return x+1; } };
int f(){ return A().m(1); }
