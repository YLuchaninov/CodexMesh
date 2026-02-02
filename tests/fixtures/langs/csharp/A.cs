
using System;

public class A {
  public int M(int x) => x + 1;
  public static int F() => new A().M(1);
}
