
package p;
import java.util.*;

public class A {
  public int m(int x) { return x + 1; }
  public static int f() { return new A().m(1); }
}
