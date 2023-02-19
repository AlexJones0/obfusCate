## **Currently Known Bugs/Issues/Limitations**
 - Due to many issues with pycparser handling these cases, the program does not currently support
   the use of **static assertions** and **pragmas**. Static assertions should be fine but often
   cause pycparser to crash for unknown reasons, and **pragmas** are ignored due to scope - the
   additional complexity of parsing every single pragma rule (e.g. setting a startup function)
   when handling identifier renaming (used in many obfuscation techniques) is too much for the
   scope of this project. Examples of these features are shown below.
   ```
   static_assert(sizeof(int) == 2 * sizeof(short), "The program requires an integer is the size of 2 shorts.");
   #pragma startup myfunc
   #pragma omp parallel for
   ```
   
 - The **Function Interface/Argument Randomisation** obfuscation mehod does not work with 
   **alised function pointer calls**, as to transform these cases to match the new function
   signatures would require a solution to pointer aliasing, which is computationally intractable
   in many cases and undecidable in others. Such, this is a feature in C which is simply too
   powerful for this obfuscation to apply to.
   ```
   int f(int x) { printf("%d\n", x); }
   int main() {
       void (*p)(int) = &f;
       (*p)(10);
   }
   ```

 - Due to a (suspected) problem with how pycparser handles generating
   declaration lists, it does not **collect modified anonymous structured
   types together**. This means that two structs defined on the same line
   may technically have different types even though they are the same
   struct, and this can break some C features via this aliasing, such
   as assigning arrays wrapped in structs using anonymous structs, e.g.:
     ```    
     struct { int arr[2]; } s1 = { {5, 6} }, s2 = { {7, 8} };
    s1 = s2;  // This works normally, but not after any obfuscating.
    ```

 - Due to a limitation in how pycparser handles case parsing, some issues can arise - pycparser attempts to parse the individual cases (as labels to compounds - sequences of statements) out of switches, which is useful in *99.9%* of real-world cases. However, switch-statements do not actually follow these semantics, and thus this abstraction does not represent all cases. This design decision is entrenched in the code and cannot be easily modified, and thus this is left as a known issue (we cannot obfuscate programs with labelled case labels) and a limitation of using pycparser for the parsing logic.  For example, if you put a label before a case label, **pycparser does not parse this correctly**, e.g. 
 ```
  int x = 1;
  switch (x) {
    case 1: goto L;
    case 2: x = 4; break;
    L:
    case 3: x = 5; break
    default: x = -1;
  }
  ``` 

 - ...