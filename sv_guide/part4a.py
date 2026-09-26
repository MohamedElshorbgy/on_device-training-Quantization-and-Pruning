"""Part IV - SystemVerilog for Verification, first half (Chapters 18-21).

Chapters 22-24 of this part are written in sv_guide/part4b.py (no part()
divider there).

Every example with an out() card was compiled and run in this environment:
classes, fork/join, process, events, semaphores, mailboxes and clocking
blocks with Verilator 5.020 (verilator --binary --timing -Wall); scheduling-
region, race, loop-variable and timeunit examples with Icarus Verilog 12
(iverilog -g2012 -Wall / vvp), because Verilator's scheduler deviates from
IEEE 1800 in those corner cases (the text points out each deviation that was
observed). Constraint-solving examples are shown without output: Verilator
5.020 accepts the syntax but ignores the constraints, so they need a
commercial simulator (Questa, VCS, Xcelium, Riviera-PRO).
"""

from sv_guide.common import *  # noqa: F401,F403


def part4a():
    part("SystemVerilog for Verification",
         "SystemVerilog became the language of chip verification because it "
         "added a real programming language to Verilog: classes with "
         "inheritance and polymorphism, a constraint solver that generates "
         "legal random stimulus, threads that communicate through events, "
         "semaphores and mailboxes, clocking blocks and a scheduler with "
         "dedicated regions for race-free testbenches, a temporal assertion "
         "language (SVA), functional coverage, and the DPI to call C, C++ "
         "and Python models. This part teaches each of these features at "
         "language-reference depth (Chapters 18-24): what the LRM guarantees, "
         "what simulators actually do, and how each construct is used by the "
         "verification engineers who sign off SoCs and by UVM, which is "
         "built entirely from them.")
    ch18()
    ch19()
    ch20()
    ch21()


# =============================================================================
#            Chapter 18 - Object-oriented programming
# =============================================================================
def ch18():
    chapter("Object-Oriented Programming: Classes, Inheritance, Polymorphism, "
            "Parameterized and Interface Classes", newpage=False)
    p("Everything in Part III describes hardware: modules, nets and "
      "variables that exist from time zero to the end of simulation and "
      "whose number is fixed at elaboration. A testbench needs something "
      "different. It creates thousands of transactions, keeps some of them "
      "in a scoreboard, throws others away, builds different components "
      "depending on the test, and wants to reuse one driver across ten "
      "projects by overriding only a few methods. SystemVerilog answers with "
      "**classes**: dynamically created, garbage-collected objects with "
      "single inheritance, virtual methods, parameterization and interface "
      "classes - essentially the object model of Java, grafted onto Verilog "
      "and its event scheduler.")
    p("Classes are a **verification** feature. No synthesis tool accepts "
      "them in RTL (a handful accept classes used purely as compile-time "
      "namespaces for static functions, but do not rely on it). Every "
      "UVM component, sequence item, register model and scoreboard is a "
      "class, so fluency with the rules in this chapter - handle semantics, "
      "copy semantics, virtual dispatch, `$cast`, parameterized classes - is "
      "a hard prerequisite for Chapters 25 and 26. All examples below were "
      "compiled and run with Verilator 5.020 (`--binary --timing`); the "
      "output cards are pasted from those runs.")

    h2("Classes, objects and handles")
    p("A **class** is a type that bundles data (**properties**) with the "
      "code that operates on it (**methods**: tasks and functions). A class "
      "declaration allocates nothing. Memory is allocated only when "
      "`new` constructs an **object** (an instance), and objects are "
      "reached exclusively through **handles** - typed, safe references "
      "that behave like pointers without pointer arithmetic. A handle that "
      "points nowhere holds the special value `null`, which is also the "
      "default value of every class variable.")
    tbl(["Concept", "Module", "struct", "class"],
        [["Created", "At elaboration, fixed count", "With the variable "
          "that holds it", "At run time by `new`, any number"],
         ["Lifetime", "Whole simulation", "Scope of the variable",
          "Until no handle refers to it (garbage collected)"],
         ["Assignment copies", "n/a (instances are not values)",
          "The whole value", "Only the **handle**; both then name one object"],
         ["Contains", "Processes, nets, instances", "Data only",
          "Data + tasks/functions; no always/initial, no nets"],
         ["Inheritance", "No", "No", "Single inheritance + interface classes"],
         ["Synthesizable", "Yes", "Yes (packed or unpacked)", "No"]],
        widths=[16, 26, 24, 34], bold_first=True,
        caption="Modules, structs and classes compared.")
    code([
        'class Packet;',
        '  // properties (class members); default lifetime: one copy per object',
        '  bit [7:0]  addr;',
        '  bit [31:0] data;',
        '  static int count = 0;       // one copy shared by ALL Packet objects',
        '  int        id;',
        '',
        "  function new(bit [7:0] addr = 8'h00, bit [31:0] data = 0);",
        "    this.addr = addr;          // 'this' disambiguates member vs argument",
        '    this.data = data;',
        '    id = count++;              // unique id per object',
        '  endfunction',
        '',
        '  function string sprint();',
        '    return $sformatf("Packet#%0d addr=%02h data=%08h", id, addr, data);',
        '  endfunction',
        '',
        '  static function int get_count();   // may touch only static members',
        '    return count;',
        '  endfunction',
        'endclass',
        '',
        'module top;',
        '  Packet p1, p2, p3;             // handles, all null initially',
        '  initial begin',
        '    if (p1 == null) $display("p1 is null before new()");',
        "    p1 = new(8'h10, 32'hCAFE_F00D);",
        '    p2 = new();                  // default arguments',
        '    p3 = p1;                     // copy the HANDLE: p3 and p1 name ONE object',
        "    p3.addr = 8'h99;",
        '    $display("%s", p1.sprint());',
        '    $display("%s", p2.sprint());',
        '    $display("p1==p3: %0b  p1==p2: %0b", p1 == p3, p1 == p2);',
        '    $display("objects created: %0d (via class scope: %0d)",',
        '             p1.get_count(), Packet::get_count());',
        '    p1 = null; p3 = null;        // object 0 is now unreachable -> reclaimed',
        '    $display("p2 still valid: %s", p2.sprint());',
        '    $finish;',
        '  end',
        'endmodule'],
         "c18_basic.sv - properties, constructor with default arguments, "
         "`this`, a static counter and a static method, and handle copying.")
    out([
        'p1 is null before new()',
        'Packet#0 addr=99 data=cafef00d',
        'Packet#1 addr=00 data=00000000',
        'p1==p3: 1  p1==p2: 0',
        'objects created: 2 (via class scope: 2)',
        'p2 still valid: Packet#1 addr=00 data=00000000',
        '- top.sv:38: Verilog $finish'], "Verilator 5.020 output.")
    p("Read the output line by line, because each line is a rule:")
    bul(["**Handles start as null.** Calling a method or touching a "
         "property through a null handle is a run-time fatal error "
         "(Verilator 5.020 aborts with 'Null pointer dereferenced' and "
         "the source line; commercial simulators report a null object "
         "access and stop). Always "
         "construct before use, and test `h == null` when a handle is "
         "optional.",
         "`p3 = p1` **copies the handle, not the object.** Writing "
         "`p3.addr` changed what `p1` sees, because there is only one object. "
         "Handle equality (`==`) compares identity, not contents.",
         "**The constructor** is the function called `new`. It has no return "
         "type (it implicitly returns the new object), may have arguments "
         "with defaults, and if you do not write one the compiler provides "
         "an implicit `new()` that only runs the property initializers. "
         "Inside `new`, property declaration initializers "
         "(`int count = 0;`) execute first - after the implicit or explicit "
         "`super.new()` - and then the body.",
         "`this` is a handle to the current object. It is needed only "
         "when a local name (here the arguments `addr` and `data`) hides a "
         "property; Verilator warns about the hiding (VARHIDDEN), which is "
         "exactly the situation where `this.` is required.",
         "**Static properties** exist once per class, not per object - "
         "`count` is shared, and is how the objects got ids 0 and 1. A "
         "**static method** has no `this`, so it may only use static "
         "members; it can be called through a handle or, more clearly, with "
         "the class scope operator: `Packet::get_count()`."])
    box("key", "Methods of a class are always automatic",
        "Tasks and functions declared inside a class have automatic "
        "lifetime: every call gets fresh local variables, so methods are "
        "re-entrant and can be called from many threads at once. The LRM "
        "makes it illegal to give a class method a static lifetime "
        "(`function static ...`). Do not confuse this with a **static "
        "method** (`static function ...`), which is about belonging to the "
        "class instead of an object, not about variable lifetime.")

    h3("Object lifetime and garbage collection")
    p("SystemVerilog has no `delete` and no destructor. An object is "
      "reclaimed automatically once no handle anywhere refers to it; in the "
      "example, the first Packet became garbage when both `p1` and `p3` were "
      "set to `null`. You never free memory explicitly, but you can still "
      "leak it: every handle kept in a queue, an associative array, a "
      "mailbox or a static variable keeps its object alive. A scoreboard "
      "that pushes expected transactions and never pops the matched ones is "
      "the classic memory leak of long regressions - the simulation slows "
      "down and eventually runs out of memory after hours, not seconds.")
    box("tip", "Where this shows up in DV",
        "UVM sequence items are created by the thousand (`new` or the "
        "factory's `create`), passed by handle through TLM ports, and "
        "dropped when the scoreboard is done with them. Because only handles "
        "move, passing a large transaction through five components costs "
        "nothing - but it also means every component sees the __same__ "
        "object. A monitor that reuses one object for every observed "
        "transaction will corrupt everything its subscribers stored. The "
        "rule: construct a new object per transaction, or clone before "
        "storing.")

    h2("Copying objects: handle copy, shallow copy, deep copy")
    p("There are three different things people mean by 'copy', and "
      "confusing them is one of the most common testbench bugs:")
    tbl(["Syntax", "What is copied", "Constructor called?"],
        [["`b = a;`", "The handle only. One object, two names.", "No"],
         ["`b = new a;`", "**Shallow copy**: a new object whose properties "
          "are copied from `a`. Properties that are handles are copied as "
          "handles, so nested objects are **shared**.",
          "No - `new a` copies memory; `new()` is not executed"],
         ["`b = a.clone();`", "**Deep copy**: user-written method that "
          "creates a new object and recursively copies nested objects.",
          "Yes, explicitly, inside `clone()`"]],
        widths=[18, 60, 22], bold_first=True)
    code([
        'class Header;',
        '  int len;',
        '  function new(int len = 0); this.len = len; endfunction',
        'endclass',
        '',
        'class Frame;',
        '  int    seq;',
        '  Header hdr;                          // a handle to another object',
        '  function new(); hdr = new(4); endfunction',
        '  // deep copy: copy scalars AND clone every object we point to',
        '  function Frame clone();',
        '    clone = new();',
        '    clone.seq     = seq;',
        '    clone.hdr.len = hdr.len;           // new() already built a fresh Header',
        '  endfunction',
        'endclass',
        '',
        'module top;',
        '  Frame a, s, d;',
        '  initial begin',
        '    a = new();  a.seq = 1;',
        '    s = new a;                         // SHALLOW copy (built-in, no constructor call)',
        '    d = a.clone();                     // DEEP copy (user-written)',
        '    a.seq = 2; a.hdr.len = 99;         // modify the original',
        '    $display("orig   : seq=%0d hdr.len=%0d", a.seq, a.hdr.len);',
        '    $display("shallow: seq=%0d hdr.len=%0d  (hdr shared: %0b)",',
        '             s.seq, s.hdr.len, s.hdr == a.hdr);',
        '    $display("deep   : seq=%0d hdr.len=%0d  (hdr shared: %0b)",',
        '             d.seq, d.hdr.len, d.hdr == a.hdr);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c18_copy.sv - shallow copy with `new a` versus a hand-written deep "
         "copy.")
    out([
        'orig   : seq=2 hdr.len=99',
        'shallow: seq=1 hdr.len=99  (hdr shared: 1)',
        'deep   : seq=1 hdr.len=4  (hdr shared: 0)',
        '- top.sv:30: Verilog $finish'], "Verilator 5.020 output.")
    p("After the original was modified, the shallow copy still has its own "
      "`seq` (scalars are copied) but reports `hdr.len=99` because its "
      "`hdr` handle points to the original's Header. The deep copy is fully "
      "independent. Note also that `new a` is resolved from **declared** "
      "types at compile time, not from the object's run-time type, so it "
      "is not polymorphic: shallow-copying through a base-class handle is "
      "not a reliable way to duplicate a derived object. That is why real "
      "code uses a virtual "
      "`copy`/`clone` method (UVM: `uvm_object::clone()` and the "
      "user-overridden `do_copy()`), which works polymorphically.")

    h2("Inheritance, super and method overriding")
    p("A class can **extend** exactly one parent (base) class. The child "
      "(derived) class inherits every property and method, may add new "
      "ones, and may **override** inherited methods by redeclaring them "
      "with the same name. Inside the child, `super.` refers to the "
      "parent's version of an overridden member. Constructors chain: the "
      "first statement of a derived `new` must be `super.new(...)`; if you "
      "omit it, the compiler inserts `super.new()` with no arguments, which "
      "is a compile error when the parent's constructor has arguments "
      "without defaults. SystemVerilog-2012 also allows passing the "
      "arguments in the declaration: `class Derived extends Base(5);`.")
    code([
        'class Base;',
        '  int x = 1;',
        '  function new(int x = 1); this.x = x; endfunction',
        '  function string kind();         return "Base"; endfunction  // NOT virtual',
        '  virtual function string vkind(); return "Base"; endfunction  // virtual',
        '  virtual function void show();',
        '    $display("  %s/%s x=%0d", kind(), vkind(), x);',
        '  endfunction',
        'endclass',
        '',
        'class Derived extends Base;',
        '  int y;',
        '  function new(int x = 5, int y = 7);',
        '    super.new(x);                     // must be the first statement',
        '    this.y = y;',
        '  endfunction',
        '  function string kind();         return "Derived"; endfunction',
        '  virtual function string vkind(); return "Derived"; endfunction',
        '  virtual function void show();',
        "    super.show();                     // reuse the parent's version",
        '    $display("  ...plus y=%0d", y);',
        '  endfunction',
        'endclass',
        '',
        'module top;',
        '  Base    b;',
        '  Derived d, d2;',
        '  initial begin',
        '    d = new();',
        '    b = d;                            // upcast: always legal, implicit',
        '    $display("b.kind()=%s  b.vkind()=%s", b.kind(), b.vkind());',
        '    $display("b.show():"); b.show();',
        '    // downcast: must be checked at run time with $cast',
        '    if ($cast(d2, b)) $display("$cast ok, d2.y=%0d", d2.y);',
        '    b = new(3);                       // now b points to a real Base',
        '    if (!$cast(d2, b)) $display("$cast failed: b holds a Base, not a Derived");',
        '    $finish;',
        '  end',
        'endmodule'],
         "c18_poly.sv - `super.new`, `super.show()`, a non-virtual versus a "
         "virtual method, and up/down-casting.")
    out([
        'b.kind()=Base  b.vkind()=Derived',
        'b.show():',
        '  Base/Derived x=5',
        '  ...plus y=7',
        '$cast ok, d2.y=7',
        '$cast failed: b holds a Base, not a Derived',
        '- top.sv:37: Verilog $finish'], "Verilator 5.020 output.")

    h3("Virtual methods and polymorphism")
    p("The handle `b` has declared type Base but refers to a Derived "
      "object. The two calls behave differently, and this is the single "
      "most important rule of SystemVerilog OOP:")
    bul(["For a **non-virtual** method the method is chosen at compile "
         "time from the **type of the handle**: `b.kind()` runs Base::kind "
         "and prints 'Base'.",
         "For a **virtual** method it is chosen at run time from the **type "
         "of the object**: `b.vkind()` runs Derived::vkind. This is "
         "**polymorphism** (dynamic dispatch).",
         "`b.show()` dispatched to Derived::show (virtual), which called "
         "`super.show()`. Inside Base::show, the call to `kind()` "
         "(non-virtual) bound to Base::kind while `vkind()` (virtual) again "
         "reached Derived::vkind - hence 'Base/Derived'.",
         "Once a method is virtual it stays virtual in every descendant, "
         "whether or not the keyword is repeated. An override must match "
         "the prototype: same argument names, types, directions and "
         "qualifiers, and the same return type (or, for a class return "
         "type, a type derived from it)."])
    box("key", "Why UVM is built on virtual methods",
        "A UVM environment holds components through base-class handles "
        "(`uvm_component`, `uvm_driver #(REQ)`) and calls `build_phase`, "
        "`run_phase`, `do_copy`, `convert2string` on them. Because those "
        "methods are virtual, your overrides run. The **factory** goes one "
        "step further: it lets a test replace the __class__ that gets "
        "constructed (`set_type_override`), and virtual dispatch makes the "
        "rest of the environment use the new behaviour without editing a "
        "line. Forgetting `virtual` on a method you intend to override is "
        "a silent bug: the code compiles and the base version runs.")

    h3("Upcasting, downcasting and $cast")
    p("Assigning a derived handle to a base handle (**upcast**) is always "
      "legal and implicit, because every Derived __is a__ Base. The "
      "reverse (**downcast**) is legal only if the object really is of the "
      "target type (or derived from it), which is known only at run time, "
      "so it requires `$cast`:")
    tbl(["Form", "On failure", "Use when"],
        [["`if ($cast(dst, src)) ...` (function)",
          "Returns 0, `dst` unchanged, no message",
          "You want to test the type (e.g. 'is this a WriteTxn?')"],
         ["`$cast(dst, src);` (task)",
          "Run-time **error**; simulation continues or stops per tool",
          "Failure is a bug; you want to hear about it"],
         ["`dst = src;` with base-typed `src`",
          "**Compile** error", "Never; this is what $cast is for"]],
        widths=[33, 35, 32], bold_first=True)
    p("`$cast` also converts between enum and integral types with a range "
      "check (Chapter 12). With a `null` source, the class form of `$cast` "
      "succeeds and assigns `null`. In UVM you will see it in every "
      "`do_copy` and `do_compare`: the argument arrives as a "
      "`uvm_object` handle and is downcast to the concrete item type.")

    h2("Abstract classes, pure virtual methods, extern and visibility")
    p("A class declared `virtual class` is **abstract**: it cannot be "
      "constructed, only extended. It typically declares **pure virtual** "
      "methods - prototypes without a body, `pure virtual function ...;` - "
      "that every non-abstract descendant must implement. This is how a "
      "framework specifies what a user must provide (UVM's `uvm_object`, "
      "`uvm_component`, `uvm_sequence_base` are all virtual classes). "
      "Methods may also be declared `extern` in the class and defined "
      "later with the class scope operator, `function void Shape::report();`, "
      "which keeps long class declarations readable and lets a header-like "
      "declaration sit in a package while bodies follow.")
    code([
        'virtual class Shape;                  // abstract: cannot be constructed',
        '  protected string name;',
        '  function new(string name); this.name = name; endfunction',
        '  pure virtual function real area();  // no body: every child MUST implement',
        '  extern function void report();      // body defined outside the class',
        'endclass',
        '',
        'function void Shape::report();        // out-of-block (extern) definition',
        '  $display("%-8s area = %6.2f", name, area());',
        'endfunction',
        '',
        'class Rect extends Shape;',
        '  local real w, h;                    // visible only inside Rect',
        '  function new(real w, real h); super.new("rect"); this.w = w; this.h = h; endfunction',
        '  virtual function real area(); return w * h; endfunction',
        'endclass',
        '',
        'class Circle extends Shape;',
        '  local real r;',
        '  function new(real r); super.new("circle"); this.r = r; endfunction',
        '  virtual function real area(); return 3.14159 * r * r; endfunction',
        'endclass',
        '',
        'module top;',
        '  Shape shapes[$];                    // queue of BASE handles',
        '  real  total;',
        '  initial begin',
        '    Rect   r;',
        '    Circle c;',
        '    r = new(2.0, 3.5);',
        '    c = new(1.0);',
        '    shapes.push_back(r);',
        '    shapes.push_back(c);',
        '    foreach (shapes[i]) shapes[i].report();   // dynamic dispatch per object',
        '    total = 0;',
        '    foreach (shapes[i]) total += shapes[i].area();',
        '    $display("total    area = %6.2f", total);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c18_abstract.sv - an abstract base with a pure virtual method, an "
         "extern method, protected and local members, and a queue of base "
         "handles dispatched polymorphically.")
    out([
        'rect     area =   7.00',
        'circle   area =   3.14',
        'total    area =  10.14',
        '- top.sv:38: Verilog $finish'], "Verilator 5.020 output.")
    p("The base method `report()` calls `area()`, which does not exist in "
      "Shape; at run time the call reaches Rect::area or Circle::area. The "
      "loop over `shapes` knows nothing about rectangles or circles - add "
      "a Triangle class and the loop does not change. That is the payoff "
      "of polymorphism for a testbench: a scoreboard iterates over "
      "`uvm_sequence_item` handles; a sequencer arbitrates between "
      "sequences it knows only by base type.")
    tbl(["Qualifier", "Visible in the class", "Visible in derived classes",
         "Visible outside"],
        [["(none) = public", "Yes", "Yes", "Yes"],
         ["`protected`", "Yes", "Yes", "No"],
         ["`local`", "Yes", "No", "No"]],
        widths=[25, 25, 25, 25], bold_first=True,
        caption="Member visibility. `const` (read-only after construction) "
                "and `static` combine freely with these qualifiers.")
    p("Violations are compile-time errors. Here is what Verilator reports "
      "for the two classic mistakes, constructing an abstract class and "
      "reading a `local` property from outside (two separate runs, one "
      "error each):")
    code([
        'virtual class Shape;',
        '  pure virtual function real area();',
        'endclass',
        'class Rect extends Shape;',
        '  local real w = 2.0;',
        '  virtual function real area(); return w * w; endfunction',
        'endclass',
        'module top;',
        '  initial begin',
        '    Shape s;',
        '    Rect  r;',
        '    r = new();',
        '    s = new();                        // ERROR 1: abstract class',
        '    $display("%f", r.w);              // ERROR 2: local member',
        '  end',
        'endmodule'], "c18_bad.sv - two deliberate errors.")
    out(["%Error: top.sv:13:9: Illegal to call 'new' using an abstract "
         "virtual class 'Shape' (IEEE 1800-2017 8.21)",
         "%Error-ENCAPSULATED: top.sv:14:22: 'w' is hidden as 'local' "
         "within this context (IEEE 1800-2017 8.18)"],
        "verilator --lint-only, first error line of each run.")
    box("expert", "local is per class, not per object",
        "Access control is checked against the __class__ in which the code "
        "is written, not the object. A method of Rect may read `other.w` "
        "of another Rect object even though `w` is local. That is what "
        "makes `compare(Rect other)` and `copy(Rect rhs)` implementable "
        "without public getters. Interview variant: 'Can a derived class "
        "read a local member of its parent?' - No, only protected ones; "
        "it can, however, call a public or protected parent method that "
        "reads it.")
    box("warn", "Constructors are never virtual - and virtual calls inside new()",
        "`new` cannot be declared virtual: an object's type is fixed by "
        "which class's `new` is called. A virtual method called from inside "
        "a base-class constructor does dispatch to the derived override, "
        "but the derived part of the object has not been initialized yet "
        "(its property initializers and constructor body run after "
        "`super.new()` returns). Keep constructors trivial; this is exactly "
        "why UVM moves construction of sub-components into `build_phase`.")

    h2("Parameterized classes")
    p("Classes take parameters like modules: **value parameters** "
      "(`int DEPTH = 4`) and **type parameters** (`type T = int`). A "
      "parameterized class is a __generic class__; each distinct set of "
      "actual parameters creates a **specialization**, which is a "
      "separate type. Two specializations are assignment-incompatible even "
      "if they look alike, and - a favourite interview question - each "
      "specialization has its **own copy of the static members**.")
    code([
        '// A generic bounded stack: T is a TYPE parameter, DEPTH a VALUE parameter',
        'class Stack #(type T = int, int DEPTH = 4);',
        '  static int n_stacks = 0;            // one copy PER SPECIALIZATION',
        '  local T items[$];',
        '  function new(); n_stacks++; endfunction',
        '  function bit push(T v);',
        '    if (items.size() == DEPTH) return 0;   // full',
        '    items.push_back(v);  return 1;',
        '  endfunction',
        '  function T pop(); return items.pop_back(); endfunction',
        '  function int size(); return items.size(); endfunction',
        'endclass',
        '',
        'typedef Stack#(string, 2) StrStack;   // name a specialization',
        '',
        'module top;',
        '  Stack #()          si1, si2;        // defaults: Stack#(int,4)',
        '  Stack #(int, 4)    si3;             // SAME specialization as #()',
        '  StrStack           ss;',
        '  initial begin',
        '    si1 = new(); si2 = new(); si3 = new(); ss = new();',
        '    void\'(ss.push("a")); void\'(ss.push("b"));',
        '    $display("push to full StrStack returns %0d", ss.push("c"));',
        '    $display("pop -> %s, size now %0d", ss.pop(), ss.size());',
        '    $display("Stack#(int,4)::n_stacks = %0d", Stack#(int,4)::n_stacks);',
        '    $display("StrStack::n_stacks      = %0d", StrStack::n_stacks);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c18_param.sv - a generic stack with a type and a value parameter; "
         "static members per specialization.")
    out([
        'push to full StrStack returns 0',
        'pop -> b, size now 1',
        'Stack#(int,4)::n_stacks = 3',
        'StrStack::n_stacks      = 1',
        '- top.sv:27: Verilog $finish'], "Verilator 5.020 output.")
    p("`Stack #()`, `Stack #(int, 4)` and the default parameter values "
      "name the same specialization, so three objects were counted there, "
      "while the string specialization counted one. A `typedef` gives a "
      "specialization a short name - essential when the same specialized "
      "type appears in many places (UVM: `typedef uvm_sequencer "
      "#(bus_item) bus_sequencer;`). Outside the class, reach static "
      "members and typedefs of a specialization with `Stack#(int,4)::name`; "
      "the bare `Stack::name` refers to the generic class and is legal only "
      "inside the class itself or in its out-of-block (extern) method "
      "definitions.")
    tbl(["Use of ::", "Example"],
        [["Static property / method", "`Packet::count`, `Config::get()`"],
         ["Typedef or enum inside a class", "`bus_item::kind_e`"],
         ["Parameter of a specialization", "`Stack#(int,4)::DEPTH`"],
         ["Out-of-block method body", "`function void Shape::report();`"],
         ["Package item (Chapter 15)", "`uvm_pkg::uvm_report_info`"],
         ["Parent version (inside class)", "`super.new()`, `super.show()` "
          "- uses `.` not `::`"]],
        widths=[40, 60], bold_first=True,
        caption="The class scope resolution operator.")
    box("tip", "Type parameters are how UVM stays type-safe",
        "`uvm_driver #(REQ, RSP)`, `uvm_sequencer #(REQ)`, "
        "`uvm_analysis_port #(T)`, `uvm_tlm_fifo #(T)` and "
        "`uvm_config_db #(T)` are all parameterized classes. Getting the "
        "parameter wrong (a driver of `bus_item` connected to a sequencer "
        "of `base_item`) is a compile-time type error, not a run-time "
        "surprise - which is the whole point. And because statics are per "
        "specialization, `uvm_config_db#(int)` and "
        "`uvm_config_db#(virtual bus_if)` are separate databases: a `set` "
        "with one type is invisible to a `get` with another.")

    h2("Forward declarations with typedef class")
    p("A class can only be used after it is declared. Two classes that "
      "refer to each other - a driver and its sequencer, a register and "
      "its block, a producer and a consumer - need a **forward "
      "declaration**: `typedef class Name;` announces that a class of that "
      "name will be defined later in the same scope.")
    code([
        'typedef class Consumer;               // forward declaration: name used before defined',
        '',
        'class Producer;',
        '  Consumer peer;                      // legal thanks to the typedef above',
        '  function void send(int v); peer.take(v); endfunction',
        'endclass',
        '',
        'class Consumer;',
        '  Producer peer;',
        '  int total;',
        '  function void take(int v); total += v; endfunction',
        'endclass',
        '',
        'module top;',
        '  initial begin',
        '    Producer p;',
        '    Consumer c;',
        '    p = new();',
        '    c = new();',
        '    p.peer = c; c.peer = p;            // two objects that reference each other',
        '    p.send(3); p.send(4);',
        '    $display("consumer total = %0d", c.total);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c18_fwd.sv - mutually referencing classes.")
    out([
        'consumer total = 7',
        '- top.sv:23: Verilog $finish'], "Verilator 5.020 output.")
    p("Circular references like this one are also why garbage collection "
      "is not simple reference counting: the two objects refer to each "
      "other, and are still reclaimed once nothing __outside__ them does. "
      "Forward typedefs are also used for parameterized classes "
      "(`typedef class Stack;` then `Stack #(int) s;` later).")

    h2("Interface classes")
    p("Single inheritance cannot express 'this transaction is both "
      "printable and comparable', and deep hierarchies that try to make "
      "one base class do everything become brittle. SystemVerilog-2012 "
      "added **interface classes** (unrelated to the `interface` construct "
      "of Chapter 16): a declaration of a set of pure virtual methods with "
      "no data. A class **implements** any number of them in addition to "
      "extending at most one class.")
    code([
        'interface class Printable;            // only pure virtual methods (+ params, typedefs)',
        '  pure virtual function string to_string();',
        'endclass',
        '',
        'interface class Comparable #(type T = int);',
        '  pure virtual function int compare(T other);   // <0, 0, >0',
        'endclass',
        '',
        '// a class may implement ANY number of interface classes',
        'class BusTxn implements Printable, Comparable#(BusTxn);',
        '  int id, addr;',
        '  function new(int id, int addr); this.id = id; this.addr = addr; endfunction',
        '  virtual function string to_string();',
        '    return $sformatf("BusTxn(id=%0d, addr=%0h)", id, addr);',
        '  endfunction',
        '  virtual function int compare(BusTxn other); return addr - other.addr; endfunction',
        'endclass',
        '',
        'function automatic void log_all(Printable items[$]);   // works for ANY Printable',
        '  foreach (items[i]) $display("  %s", items[i].to_string());',
        'endfunction',
        '',
        'module top;',
        '  initial begin',
        '    BusTxn a, b;',
        '    Printable q[$];',
        "    a = new(1, 'h40);",
        "    b = new(2, 'h10);",
        '    q.push_back(a); q.push_back(b);   // implicit upcast to the interface type',
        '    log_all(q);',
        '    $display("a.compare(b) = %0d", a.compare(b));',
        '    $finish;',
        '  end',
        'endmodule'],
         "c18_iface.sv - two interface classes (one parameterized) "
         "implemented by one class, used through an interface-class "
         "handle.")
    out([
        '  BusTxn(id=1, addr=40)',
        '  BusTxn(id=2, addr=10)',
        'a.compare(b) = 48',
        '- top.sv:32: Verilog $finish'], "Verilator 5.020 output.")
    bul(["An interface class may contain only pure virtual methods, "
         "typedefs and parameters - no properties, no constraints, no "
         "method bodies, no constructor.",
         "An interface class can `extends` one or more other interface "
         "classes (multiple inheritance of **interface**, never of "
         "implementation, so the 'diamond problem' of C++ cannot occur).",
         "A class that `implements` an interface class must implement every "
         "method with a matching virtual prototype, unless the class is a "
         "`virtual class`, which may leave them as pure virtual for its "
         "children.",
         "A handle of an interface-class type can refer to any object whose "
         "class implements it, and `$cast` works between an interface class "
         "and any class that implements it."])
    box("warn", "Tool portability: combining extends and implements",
        "`class BusTxn extends Txn implements Printable, Comparable#(BusTxn);` "
        "is perfectly legal IEEE 1800-2017. In this environment, "
        "Verilator 5.020 compiled that form but failed in its C++ build "
        "when a BusTxn handle was assigned to a Printable handle, and a "
        "`$cast` workaround failed at run time; removing the `extends Txn` "
        "(as in the listing above) made it work. Interface classes are "
        "newer than the rest of SV OOP, and support is still uneven across "
        "simulators and linters - test your pattern on every tool in your "
        "flow before building a library on it.")

    h2("Design patterns you will meet: the singleton")
    p("Some objects must exist exactly once: a global configuration, a "
      "report server, a factory. The **singleton** pattern hides the "
      "constructor (`local function new`) and offers a static `get()` "
      "that constructs the single instance on first use.")
    code([
        'class Config;',
        '  local static Config m_inst;         // the one and only instance',
        '  int verbosity = 1;',
        '  local function new(); $display("  Config constructed"); endfunction  // no outside new',
        '  static function Config get();',
        '    if (m_inst == null) m_inst = new();     // lazy construction on first use',
        '    return m_inst;',
        '  endfunction',
        'endclass',
        '',
        'module top;',
        '  initial begin',
        '    Config c1, c2;',
        '    c1 = Config::get();',
        '    c1.verbosity = 3;',
        '    c2 = Config::get();               // same object, no second construction',
        '    $display("same object: %0b, c2.verbosity=%0d", c1 == c2, c2.verbosity);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c18_single.sv - a lazily constructed singleton.")
    out([
        '  Config constructed',
        'same object: 1, c2.verbosity=3',
        '- top.sv:18: Verilog $finish'], "Verilator 5.020 output.")
    p("UVM is full of singletons: `uvm_root` (the implicit top of the "
      "component tree, reached with `uvm_root::get()`), `uvm_factory`, the "
      "report server and the resource pool behind `uvm_config_db`. Other "
      "patterns you will recognize later: the **factory** (construct by "
      "type name, override per test), the **observer** (analysis ports "
      "broadcasting to subscribers), the **strategy** (a driver delegating "
      "to a swappable protocol object) and **callbacks** (user hooks "
      "registered at run time).")

    h2("Summary")
    bul(["A class is a type; `new` creates objects at run time; handles "
         "refer to objects and default to `null`. Assignment copies handles, "
         "not objects.",
         "Objects are garbage collected when unreachable; memory leaks come "
         "from handles kept in containers.",
         "Static members are shared per class (per **specialization** for "
         "parameterized classes); static methods have no `this`. Class "
         "methods always have automatic lifetime.",
         "`new a` is a shallow copy that does not run the constructor and "
         "shares nested objects; write a virtual clone/copy for deep copies.",
         "Non-virtual methods bind by handle type at compile time; virtual "
         "methods bind by object type at run time. Once virtual, always "
         "virtual. Constructors cannot be virtual.",
         "Upcasts are implicit; downcasts need `$cast`, whose function form "
         "returns 0 on failure.",
         "`virtual class` + `pure virtual` define abstract frameworks; "
         "`extern` separates declaration from definition; `local` and "
         "`protected` restrict visibility (per class, not per object).",
         "`typedef class` forward-declares; interface classes provide "
         "multiple inheritance of interface via `implements`.",
         "These rules are the vocabulary of UVM: base-class handles, "
         "virtual phase methods, parameterized TLM classes, singletons and "
         "the factory."])

    h2("Exercises")
    bul(["Write a class `Counter` with a static `total` and a per-object "
         "`count`, and a method `incr()` that updates both. Create three "
         "objects, call `incr()` a different number of times on each, and "
         "print all values. Then explain what changes if `total` is not "
         "static.",
         "Extend `c18_copy.sv` with a queue of Header handles inside Frame. "
         "Show that `new a` shares the queue contents' objects, and write "
         "`clone()` so that it does not.",
         "Remove the `virtual` keyword from `vkind` in `c18_poly.sv` and "
         "predict every output line before running it. Then make `show` "
         "non-virtual in Base only and predict again.",
         "Implement `virtual function bit compare(Shape other)` in Shape "
         "and override it in Rect using `$cast` so that comparing a Rect "
         "with a Circle returns 0 instead of crashing.",
         "Create a parameterized class `Pool #(type T = int)` with a static "
         "method `get_count()`. Prove that `Pool#(int)` and `Pool#(byte)` "
         "count independently. Why does this matter for "
         "`uvm_config_db#(T)`?",
         "Interview drill: explain, without code, why a monitor that calls "
         "`new` once and then reuses that object for every observed bus "
         "transfer produces a scoreboard in which all stored transactions "
         "look identical."], ordered=True)


# =============================================================================
#            Chapter 19 - Constrained random stimulus
# =============================================================================
def ch19():
    chapter("Constrained Random Stimulus")
    p("A directed test checks the scenario its author thought of. The bugs "
      "that escape to silicon live in the scenarios nobody thought of: a "
      "burst that crosses a 4 KB boundary while the FIFO is one entry from "
      "full, during a clock-gating request. **Constrained random "
      "verification** (CRV) attacks that space statistically: you describe "
      "what a __legal__ stimulus is, with declarative constraints, and a "
      "**constraint solver** built into the simulator picks random values "
      "that satisfy all of them. Combined with self-checking and "
      "functional coverage (Chapter 23), this is the coverage-driven "
      "methodology used on essentially every commercial SoC.")
    box("warn", "Which tools in this book can run this chapter",
        "Verilator 5.020 accepts the full constraint syntax used here but "
        "**ignores the constraints** - `randomize()` fills every `rand` "
        "variable with unconstrained random bits (a constraint `a inside "
        "{[10:20]}` produced 'hc4 in our test). Icarus Verilog does not "
        "support `rand` at all. The constraint listings in this chapter "
        "therefore need a commercial simulator (Questa, VCS, Xcelium, "
        "Riviera-PRO) and are shown **without** output cards; the expected "
        "behaviour is stated in the text. The parts that do not depend on "
        "the solver - `$urandom`, seeding, the randomize hooks and the "
        "return value - were run with Verilator.")

    h2("rand, randc and randomize()")
    p("Declaring a class property `rand` makes it a **random variable**: "
      "each call of the object's built-in `randomize()` method assigns it a "
      "new value that satisfies every active constraint. `randc` is "
      "**random-cyclic**: the variable walks through a random permutation "
      "of all its possible values before any value repeats (a 2-bit "
      "`randc` returns, e.g., 2, 0, 3, 1, then a new permutation). Only "
      "integral types can be random: bit/logic vectors, integer types, "
      "enums (which take only their named values), and arrays and queues "
      "of those - whose **size** is also random unless constrained. "
      "`real` variables cannot be `rand` in IEEE 1800-2017 (IEEE 1800-2023 "
      "adds random `real` support, not yet widely implemented). A handle declared `rand` makes `randomize()` "
      "descend into the object it points to, which must not be null.")
    tbl(["Property", "rand", "randc"],
        [["Distribution", "Uniform over the solution space (unless shaped "
          "by dist / solve-before)", "Permutation: every value once per "
          "cycle"],
         ["Solved", "Together with all other rand variables", "**Before** "
          "the rand variables; its value is then a fixed input for them"],
         ["Width", "Any", "Tools may limit the width (keep it small, e.g. "
          "<= 16 bits)"],
         ["Typical use", "Addresses, data, lengths, modes",
          "Tags/IDs, register indices, 'visit every opcode' tests"]],
        widths=[20, 42, 38], bold_first=True)
    p("`randomize()` is a virtual function that returns **1 on success** "
      "and **0 when the constraints cannot be satisfied**. On failure the "
      "random variables keep their previous values and the simulator "
      "usually prints only a warning, so a test that ignores the return "
      "value silently keeps driving stale stimulus. Always check it:")
    code(["// correct: the check cannot be switched off",
          "if (!tr.randomize()) `uvm_fatal(\"RAND\", \"tr.randomize() failed\")",
          "if (!tr.randomize()) $fatal(1, \"randomize failed\");   // plain SV",
          "",
          "// WRONG: randomize() is called INSIDE the assertion",
          "assert (tr.randomize());"],
         "Checking the result of randomize().")
    box("warn", "Never call randomize() inside assert()",
        "An immediate assertion's expression is not evaluated at all when "
        "assertions are disabled (`$assertoff`, a `-nosva`-style switch, or "
        "a regression that turns assertions off for speed). "
        "`assert(tr.randomize());` then **never randomizes** - every "
        "transaction keeps its last value and the test still 'passes'. Put "
        "the call in an `if`, as above.")

    h2("Constraint blocks")
    p("A **constraint block** is a named set of Boolean expressions over "
      "random (and non-random) variables. Constraints are **declarative "
      "and bidirectional**: they are relations the solver must make true, "
      "not assignments executed in order. `len == 4` in a constraint does "
      "not 'set' len; it restricts the solution space, and the solver may "
      "satisfy `a + b == 10` by choosing `b` first. All active constraints "
      "of the object, including those inherited and those of nested `rand` "
      "objects, are solved **simultaneously**.")
    code([
        'typedef enum bit [1:0] {READ, WRITE, IDLE} kind_e;',
        '',
        'class BusTxn;',
        '  rand  kind_e     kind;',
        '  rand  bit [31:0] addr;',
        '  rand  bit [7:0]  len;                 // burst length in beats',
        '  randc bit [3:0]  tag;                 // cycles through all 16 values before repeating',
        '  rand  bit [31:0] data[];              // dynamic array: its SIZE is random too',
        '',
        "  constraint c_addr  { addr inside {[32'h0000_0000 : 32'h0000_FFFF],   // RAM window",
        "                                    [32'h4000_0000 : 32'h4000_00FF]};  // CSR window",
        "                       addr[1:0] == 2'b00; }                          // word aligned",
        '  constraint c_len   { len inside {1, 2, 4, 8, 16}; }',
        '  constraint c_data  { data.size() == len;                            // size tracks len',
        '                       foreach (data[i]) data[i] != 0; }',
        "  constraint c_csr   { addr >= 32'h4000_0000 -> len == 1; }            // CSRs: single beat",
        '  constraint c_idle  { if (kind == IDLE) { len == 1; } else { len >= 1; } }',
        'endclass'],
         "k19_basic.sv - set membership, implication, if-else, foreach and "
         "array-size constraints (needs a commercial simulator).")
    p("What a constraint-solving simulator does with this class:")
    bul(["**inside** restricts `addr` to the union of two ranges; `[lo:hi]` "
         "is inclusive and ranges and single values may be mixed. Every "
         "legal value is equally likely, so the 64 KB RAM window is hit "
         "about 256 times more often than the 256-byte CSR window - a "
         "distribution effect you will usually want to reshape with `dist`.",
         "**Implication** `P -> Q` means 'if P then Q' (it is equivalent "
         "to `!P || Q`): every CSR address forces `len == 1`, and "
         "because constraints are bidirectional, `len != 1` also forbids "
         "CSR addresses.",
         "**if-else** is the block form of implication and can hold several "
         "constraints per branch.",
         "**Array constraints**: `data.size() == len` sizes the dynamic "
         "array (the size is solved before the elements), and `foreach` "
         "applies a constraint to every element. Sum, product, and, or and "
         "xor reductions are also allowed: `data.sum() with (int'(item)) < "
         "1000`.",
         "**randc tag** is solved first and cycles through all 16 values.",
         "Every `rand` variable not mentioned in any constraint is simply "
         "uniform over its type."])
    p("For comparison, here is what Verilator reports when it meets a "
      "constraint block - it is a warning, not an error, and the "
      "constraint is dropped:")
    out(["%Warning-CONSTRAINTIGN: top.sv:4:14: Constraint ignored (unsupported)",
         "    4 |   constraint c_a { a dist { 0 := 40, [1:3] := 20, [4:15] :/ 20 }; }",
         "%Warning-CONSTRAINTIGN: top.sv:8:14: Constraint ignored (unsupported)"],
        "verilator --lint-only -Wall on k19_dist.sv (excerpt). A reminder "
        "to check what your tool supports before trusting a random test.")
    box("warn", "Width and sign in constraints",
        "Constraint expressions follow the normal SystemVerilog expression "
        "rules of Chapter 4 - including silent truncation. With `rand bit "
        "[7:0] a, b;` the constraint `a + b == 300` is evaluated in the "
        "width of its largest operand, the 32-bit literal 300, so it works; "
        "but `a + b < 8'd50` is evaluated in 8 bits "
        "and wraps, so a=200, b=100 (sum 300 mod 256 = 44) satisfies it. "
        "The same trap hits `data.sum() < 1000` on a byte array: the sum is "
        "computed in the element width. Cast explicitly: "
        "`data.sum() with (int'(item)) < 1000`. Mixing signed and unsigned "
        "operands makes the comparison unsigned, so `x > -1` with an "
        "unsigned `x` is always false.")

    h2("Shaping the distribution: dist")
    p("Uniform random is rarely what you want: corner cases such as "
      "address 0, the maximum length or back-to-back errors need to be "
      "hit far more often than their share of the value space. A `dist` "
      "constraint assigns **weights**. Two operators distinguish how a "
      "weight applies to a range:")
    code([
        'class DistDemo;',
        '  rand bit [3:0] a, b;',
        '  // := weight applies to EACH value in the item; :/ divides the weight across the range',
        '  constraint c_a { a dist { 0 := 40, [1:3] := 20, [4:15] :/ 20 }; }',
        '  //   total weight = 40 + 3*20 + 20 = 120',
        '  //   P(a==0) = 40/120 = 1/3      P(a==1) = P(a==2) = P(a==3) = 20/120 = 1/6',
        '  //   P(a==k), k in 4..15 = (20/12)/120 = 1/72      (the range SHARES 20)',
        '  constraint c_b { b dist { [0:7] :/ 1, [8:15] :/ 3 }; }  // upper half 3x more likely',
        'endclass'],
         "k19_dist.sv - := (weight per value) versus :/ (weight shared by "
         "the range). The comments give the exact probabilities.")
    tbl(["Item", "Operator", "Weight of each value", "Probability"],
        [["0", ":= 40", "40", "40/120 = 33.3%"],
         ["[1:3]", ":= 20", "20 (each of 3 values)", "3 x 20/120 = 50%"],
         ["[4:15]", ":/ 20", "20/12 = 1.67 (shared by 12 values)",
          "20/120 = 16.7% in total"]],
        widths=[15, 15, 40, 30], bold_first=True,
        caption="How the weights of c_a add up.")
    bul(["A `dist` is still a hard constraint on **membership**: the value "
         "must be one of the listed values. If other constraints exclude "
         "some of them, the weights apply among the values that remain. A "
         "weight of 0 excludes a value.",
         "`dist` cannot be applied to a `randc` variable.",
         "Distributions are a property of **many** calls, not one; with "
         "other constraints active, the observed frequencies can differ "
         "noticeably from the nominal weights."])

    h2("Solution order and solve...before")
    p("The solver picks uniformly among **complete solutions**, not "
      "variable by variable. That has a surprising consequence for "
      "implications, captured in the classic example below.")
    code([
        'class SolveDemo;',
        '  rand bit       mode;                  // 1 = "long" mode',
        '  rand bit [7:0] len;',
        '  constraint c_impl  { mode -> len == 0; }   // only ONE of 257 solutions has mode==1',
        '  constraint c_order { solve mode before len; } // pick mode FIRST: P(mode==1) = 1/2',
        'endclass',
        '',
        'class Arrays;',
        '  rand bit [7:0] q[$];',
        '  rand bit [7:0] ids[4];',
        '  constraint c_size  { q.size() inside {[2:5]}; }',
        "  constraint c_sum   { q.sum() with (int'(item)) < 200; }   // widen before summing!",
        '  constraint c_sort  { foreach (q[i]) if (i > 0) q[i] > q[i-1]; }  // strictly ascending',
        '  constraint c_uniq  { unique {ids}; }                         // all four differ',
        'endclass'],
         "k19_solve.sv - solve-before, and array constraints: size, sum, "
         "ordering and unique (needs a commercial simulator).")
    p("Without `c_order`, the legal (mode, len) pairs are 256 pairs with "
      "mode=0 plus **one** pair (1, 0). Each is equally likely, so "
      "P(mode==1) = 1/257: the 'long mode' is almost never tested. "
      "`solve mode before len` tells the solver to choose `mode` first "
      "(from the values for which __some__ solution exists), then `len`: "
      "P(mode==1) becomes 1/2. `solve...before` **never changes which "
      "solutions are legal** - only their probabilities. It cannot involve "
      "`randc` variables (they are always solved first anyway), and "
      "circular orderings are an error.")
    p("The `Arrays` class shows the array toolbox: `q.size()` bounds the "
      "queue length, `sum() with` constrains a reduction (widened to "
      "`int` to avoid the wrap-around described above), the `foreach` "
      "with `i > 0` guard produces a strictly ascending list (the guard "
      "keeps `q[i-1]` in bounds), and `unique {ids}` makes all elements of "
      "the array pairwise different - a one-line replacement for an "
      "O(n^2) foreach over pairs.")

    h2("Controlling constraints: soft, override, static, constraint_mode, rand_mode")
    code([
        'class Cfg;',
        '  rand bit [7:0] burst;',
        '  rand bit [3:0] prio;',
        '  constraint c_def  { soft burst == 4; }         // default, may be overridden',
        '  constraint c_prio { prio inside {[0:7]}; }',
        '  static constraint c_global { prio != 5; }     // static: mode shared by all objects',
        'endclass',
        '',
        'class Stress extends Cfg;',
        '  constraint c_def { burst inside {[16:64]}; }  // SAME name: overrides the parent block',
        'endclass',
        '',
        'module top;',
        '  initial begin',
        '    Cfg c;',
        '    int unsigned max_burst;',
        '    c = new();',
        '    max_burst = 8;',
        '    // inline constraint beats the soft default; name resolution inside with{}:',
        '    //   unqualified names are looked up in the OBJECT first; local:: forces the caller',
        '    if (!c.randomize() with { burst == local::max_burst; prio < 3; })',
        '      $error("randomize failed");',
        '    c.c_prio.constraint_mode(0);                 // switch a block off',
        '    c.prio.rand_mode(0);                         // prio becomes a state variable',
        "    void'(c.randomize());                        // only burst is randomized now",
        "    void'(std::randomize(max_burst) with { max_burst inside {[1:16]}; });",
        '  end',
        'endmodule'],
         "k19_soft.sv - soft defaults, overriding a block by name, static "
         "constraints, inline constraints with local::, constraint_mode, "
         "rand_mode and std::randomize (needs a commercial simulator).")
    tbl(["Mechanism", "Effect"],
        [["`soft expr;`", "A default that is dropped (not an error) when it "
          "conflicts with a hard constraint. Among conflicting soft "
          "constraints, later / higher-priority ones win (inline beats "
          "class, derived beats base)."],
         ["Same-named block in a child class",
          "Replaces the parent's block entirely (`Stress::c_def` removes the "
          "soft burst == 4 and requires 16..64). This is how tests reshape "
          "stimulus without editing the transaction class."],
         ["`static constraint`", "constraint_mode() on it affects every "
          "object of the class, not just one."],
         ["`h.blk.constraint_mode(0/1)`", "Turns a block off/on for this "
          "object; `h.constraint_mode(0)` turns all blocks off. "
          "`h.blk.constraint_mode()` returns the current state."],
         ["`h.var.rand_mode(0/1)`", "Makes a rand variable a state variable "
          "(keeps its value, still usable in constraints) or random again. "
          "`h.rand_mode(0)` affects all rand variables."],
         ["`h.randomize(v1, v2)`", "Randomizes only the listed variables; "
          "all other rand variables act as state variables for this call."],
         ["`h.randomize(null)`", "Randomizes nothing; only checks whether "
          "the current values satisfy the constraints (returns 1/0)."]],
        widths=[30, 70], bold_first=True)
    p("The **inline constraint** `randomize() with { ... }` adds "
      "constraints for one call only; it is how a sequence says 'give me a "
      "random write to this address'. Name resolution inside the braces "
      "is the source of a well-known bug: unqualified names are looked up "
      "**in the object being randomized first**, and only then in the "
      "calling scope. If the class has a property called `max_burst`, "
      "`burst == max_burst` compares with the object's own property, not "
      "with your local variable. `local::max_burst` forces the caller's "
      "scope (IEEE 1800-2012 and later); `this.` or no prefix means the "
      "object. In UVM, the constraint blocks passed to "
      "macros such as uvm_do_with follow the same rule.")
    p("`std::randomize(vars) with {...}` randomizes ordinary variables "
      "(module, function or class scope) without a class: useful for a "
      "quick random delay or a local choice. The `std::` prefix is "
      "optional unless a `randomize` in scope would hide it.")

    h2("pre_randomize() and post_randomize()")
    p("Every class has two empty void functions that `randomize()` calls "
      "automatically: `pre_randomize()` before solving and "
      "`post_randomize()` after a **successful** solve (not after a "
      "failure). Override them to prepare state (switch constraint modes, "
      "size arrays, record statistics) and to compute derived fields that "
      "should not be solved - CRCs, parity, ECC, packed encodings - which "
      "is also much faster than expressing them as constraints. They are "
      "called for nested rand objects too, and a child override should "
      "call `super.pre_randomize()` / `super.post_randomize()` if the "
      "parent's version does work.")
    code([
        'class Pkt;',
        '  rand bit [7:0]  len;',
        '  rand bit [31:0] payload;',
        '       bit [7:0]  crc;                  // NOT rand: derived, never randomized',
        '  int n_pre, n_post;',
        '  function void pre_randomize();        // called BEFORE the solver',
        '    n_pre++;',
        '  endfunction',
        '  function void post_randomize();       // called AFTER a SUCCESSFUL solve',
        '    n_post++;',
        '    crc = payload[31:24] ^ payload[23:16] ^ payload[15:8] ^ payload[7:0];',
        '  endfunction',
        'endclass',
        '',
        'module top;',
        '  initial begin',
        '    Pkt p;',
        '    int ok;',
        '    p = new();',
        '    ok = p.randomize();',
        '    $display("randomize() returned %0d, pre=%0d post=%0d, payload=%h crc=%h",',
        '             ok, p.n_pre, p.n_post, p.payload, p.crc);',
        '    repeat (3) begin',
        '      if (!p.randomize()) $fatal(1, "randomize() failed");   // ALWAYS check',
        '      $display("len=%3d payload=%h crc=%h", p.len, p.payload, p.crc);',
        '    end',
        '    $display("pre_randomize calls=%0d, post_randomize calls=%0d", p.n_pre, p.n_post);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c19_hooks.sv - a derived CRC computed in post_randomize (no "
         "constraints, so it runs on Verilator).")
    out([
        'randomize() returned 1, pre=1 post=1, payload=0b1e5d9c crc=d4',
        'len=  2 payload=48c2e0e4 crc=8e',
        'len=120 payload=bbd58ebc crc=5c',
        'len=182 payload=2a14ffe4 crc=25',
        'pre_randomize calls=4, post_randomize calls=4',
        '- top.sv:28: Verilog $finish'], "Verilator 5.020 output (random values "
        "depend on the seed).")
    p("Check the arithmetic: 0b ^ 1e ^ 5d ^ 9c = d4, so the CRC was "
      "computed from the freshly randomized payload, once per call. One "
      "honest note on tool support: when this example also exercised "
      "`p.len.rand_mode(0)`, Verilator 5.020 still reported `rand_mode()` "
      "as 1 and kept randomizing `len`, so `rand_mode` is another feature "
      "to test only on a full-featured simulator.")

    h2("System random functions and seeding")
    tbl(["Function", "Returns", "Notes"],
        [["`$urandom` / `$urandom(seed)`", "32-bit **unsigned**",
          "Uses the calling thread's RNG (thread stability); the seed form "
          "reseeds that call"],
         ["`$urandom_range(max, min=0)`", "Unsigned in [min, max]",
          "Inclusive; arguments may be given in either order"],
         ["`$random` / `$random(seed_var)`", "32-bit **signed**",
          "Verilog-2001 legacy: one global generator, `inout` seed "
          "variable; `$random % 10` can be negative"],
         ["`$dist_uniform`, `$dist_normal`, ...", "Integer", "Verilog "
          "distribution functions; rarely used in modern DV"],
         ["`obj.srandom(seed)`, `process::self().srandom(seed)`", "-",
          "Seed one object's / one thread's RNG"],
         ["`get_randstate()` / `set_randstate(s)`", "string / -",
          "Save and restore an RNG state (replay one object's stream)"]],
        widths=[36, 20, 44], bold_first=True)
    code([
        'module top;',
        '  int unsigned a[6];',
        '  initial begin',
        '    foreach (a[i]) a[i] = $urandom_range(9, 0);    // inclusive; args may be swapped',
        '    $display("$urandom_range(9,0): %p", a);',
        '    foreach (a[i]) a[i] = $urandom_range(3);       // one argument: min defaults to 0',
        '    $display("$urandom_range(3)  : %p", a);',
        '    $display("$urandom           : %0d (32-bit unsigned)", $urandom);',
        '    $display("$random            : %0d (32-bit signed)", $random);',
        '    $finish;',
        '  end',
        'endmodule'], "c19_urand.sv")
    out([
        '$ ./obj_dir/Vtop',
        "$urandom_range(9,0): '{'h6, 'h4, 'h2, 'h2, 'h2, 'h2}",
        "$urandom_range(3)  : '{'h2, 'h0, 'h3, 'h3, 'h1, 'h1}",
        '$ ./obj_dir/Vtop',
        "$urandom_range(9,0): '{'h6, 'h4, 'h2, 'h2, 'h2, 'h2}",
        "$urandom_range(3)  : '{'h2, 'h0, 'h3, 'h3, 'h1, 'h1}",
        '$ ./obj_dir/Vtop +verilator+seed+1',
        "$urandom_range(9,0): '{'h0, 'h9, 'h9, 'h1, 'h6, 'h6}",
        "$urandom_range(3)  : '{'h0, 'h3, 'h0, 'h0, 'h2, 'h1}",
        '$ ./obj_dir/Vtop +verilator+seed+2',
        "$urandom_range(9,0): '{'h6, 'h3, 'h7, 'h4, 'h1, 'h4}",
        "$urandom_range(3)  : '{'h1, 'h3, 'h1, 'h3, 'h1, 'h2}"],
        "Verilator 5.020: the same binary run with the default seed "
        "(twice), and with +verilator+seed+1 and +2.")
    p("The first two runs are identical: a random simulation is fully "
      "**reproducible** from its seed, which is what makes it debuggable. "
      "Every simulator takes the seed on the command line - Questa "
      "`-sv_seed N` (or `random`), VCS `+ntb_random_seed=N`, Xcelium "
      "`-svseed N`, Verilator `+verilator+seed+N` - and a regression "
      "system runs each test with many seeds and records the seed of "
      "every failure. In Verilator 5.020 we also observed that "
      "`process::self().srandom(42)` did not reset the `$urandom` "
      "sequence of the thread, contrary to the LRM, so seed through the "
      "command line when using it.")

    h3("Random stability")
    p("IEEE 1800 defines **random stability**: every thread and every "
      "object has its own random number generator (RNG), seeded from its "
      "parent's RNG when the thread or object is created. Consequences:")
    bul(["**Thread stability**: the values a thread gets from `$urandom` "
         "do not depend on what other threads do, as long as threads are "
         "created in the same order.",
         "**Object stability**: `obj.randomize()` uses the object's own "
         "RNG, so adding a `randomize()` call on some other object does not "
         "change this object's values.",
         "Stability is **hierarchical**, not absolute: inserting a new "
         "`fork` or constructing an extra object __before__ existing ones "
         "changes the seeds handed out afterwards. A small testbench "
         "edit can therefore make a failing seed stop failing. Keep the "
         "failing seed's full environment (source revision + seed) to "
         "reproduce bugs, and add new components after existing ones "
         "where possible.",
         "`$random` is **not** stable: it has a single global stream "
         "shared by everyone; prefer `$urandom` and class randomization."])

    h2("When the solver fails: common causes and debugging")
    tbl(["Symptom", "Typical cause", "Fix"],
        [["randomize() returns 0 every time", "Two constraints contradict "
          "(e.g. inherited `len <= 8` and a test's `len == 16`)",
          "Bisect with `constraint_mode(0)` on blocks; override the block "
          "by name instead of adding a conflicting one"],
         ["Fails only with an inline with{}", "Name captured from the "
          "object instead of the caller", "Use `local::` for caller "
          "variables"],
         ["Value outside the intended range", "Width/sign wrap-around in "
          "the expression", "Widen with casts, compare with sized literals"],
         ["A mode is (almost) never generated", "Implication skews the "
          "solution count", "`solve a before b` or a `dist` on the mode"],
         ["Null object error in randomize()", "`rand` handle to a nested "
          "object that was never constructed", "Construct in `new()`"],
         ["Very slow randomize()", "Large arrays with pairwise foreach, "
          "multiplication/division/modulo on wide random variables",
          "Use `unique`, move derived values to post_randomize, reduce "
          "widths, split into stages"],
         ["Different result on another simulator", "Solver implementations "
          "differ; the LRM does not define the exact sequence", "Never "
          "compare random streams across tools; compare coverage"]],
        widths=[25, 38, 37], bold_first=True)
    p("Commercial simulators print a report that names the smallest set of "
      "conflicting constraints when a solve fails (Questa's "
      "`-solvefaildebug`, and equivalents in VCS and Xcelium) - learn the "
      "option for your tool on day one. Without it, the bisection method "
      "works everywhere: call `randomize()` in a loop while disabling "
      "constraint blocks one at a time until it succeeds.")
    box("expert", "Interview favourites",
        "(1) 'Constrain a 32-bit value to have exactly 4 bits set' - "
        "`$countones(v) == 4`. (2) 'Generate 10 unique values without "
        "unique' - `foreach (a[i]) foreach (a[j]) if (i < j) a[i] != a[j];` "
        "(then mention `unique` and randc). (3) 'Why does my 1-in-257 mode "
        "never appear?' - solution-space uniformity and `solve before`. "
        "(4) 'Difference between rand_mode(0) and removing rand?' - the "
        "former is dynamic per object and the variable still participates "
        "in constraints as a state variable. (5) 'What happens to rand "
        "variables when randomize() fails?' - they keep their old values "
        "and post_randomize() is not called.")

    h2("Summary")
    bul(["`rand` variables are solved together, uniformly over all "
         "solutions; `randc` cycles through permutations and is solved first.",
         "`randomize()` returns 1/0; check it with `if`, never inside "
         "`assert`.",
         "Constraints are declarative, bidirectional Boolean relations: "
         "`inside`, `dist`, `->`, if-else, `foreach`, `size()`, reductions, "
         "`unique`, `soft`.",
         "`:=` weights each value, `:/` shares the weight across a range; "
         "`solve before` changes probabilities, never legality.",
         "Tests reshape stimulus by overriding blocks by name, inline "
         "`with {}` (with `local::` for caller names), `constraint_mode` and "
         "`rand_mode`.",
         "`pre_randomize` / `post_randomize` prepare state and compute "
         "derived fields; post runs only on success.",
         "Random stimulus is reproducible from the seed; thread and object "
         "stability limit, but do not eliminate, seed perturbation from "
         "testbench edits.",
         "Verilator 5.020 ignores constraints: use a commercial simulator "
         "for constrained random."])

    h2("Exercises")
    bul(["Write a class for an AXI-like burst with `addr`, `len` (1-256) "
         "and `size` (1, 2, 4, 8 bytes) such that the burst never crosses a "
         "4 KB boundary, `addr` is aligned to `size`, and bursts of length "
         "1 appear 30% of the time.",
         "For `rand bit [2:0] x; rand bit y; constraint c { y -> x == 0; }` "
         "compute P(y==1) with and without `solve y before x`.",
         "Constrain a queue of 8 bytes to be a permutation of 0..7 in two "
         "different ways (with `unique` and without it).",
         "A derived test class adds `constraint c_len { len == 32; }` but "
         "the base class has `constraint c_len_max { len <= 16; }`. What "
         "happens, and give two different ways to make the test work.",
         "Explain why `if (!tr.randomize() with { addr == addr; })` does "
         "not constrain anything, and fix it.",
         "Run `c19_urand.sv` with three seeds on Verilator, then add a "
         "second `initial` block that also calls `$urandom` before the "
         "first one. Which printed values change, and what does that tell "
         "you about Verilator's thread stability?"], ordered=True)


# =============================================================================
#            Chapter 20 - Processes and inter-process communication
# =============================================================================
def ch20():
    chapter("Processes and Inter-Process Communication: fork/join, Events, "
            "Semaphores, Mailboxes")
    p("A testbench is a concurrent program. The driver waits for the bus to "
      "be free while the monitor samples every cycle, the scoreboard waits "
      "for results, a watchdog counts down, and the test decides when "
      "everything is done. Verilog gave us static processes (`initial`, "
      "`always`) and a basic `fork...join`. SystemVerilog adds dynamic "
      "process creation (`join_any`, `join_none`), process control "
      "(`wait fork`, `disable fork`, the `process` class) and three "
      "communication primitives - **events**, **semaphores** and "
      "**mailboxes** - that are the foundation of UVM's TLM ports, "
      "sequencer arbitration and objections.")
    p("All processes in a simulation run in one thread of the simulator: "
      "'parallel' means **interleaved at blocking points**, according to "
      "the scheduling rules of Chapters 5 and 21. A process runs until it "
      "blocks (a delay, an event control, a `wait`, a blocking `get`), "
      "and the order among processes that are ready in the same region is "
      "**not defined** by the LRM. Code whose result depends on that order "
      "is a race. Examples in this chapter were run with Verilator 5.020 "
      "(`--timing`) unless the caption says Icarus Verilog.")

    h2("fork...join, join_any and join_none")
    p("Each statement directly inside `fork ... join` becomes a separate "
      "child process (wrap several statements in `begin...end` to make one "
      "child). The three closing keywords differ only in **when the parent "
      "continues**:")
    tbl(["Closing keyword", "Parent continues", "Children afterwards"],
        [["`join`", "When **all** children have finished", "All done"],
         ["`join_any`", "When **any one** child has finished",
          "The others keep running"],
         ["`join_none`", "Immediately, without blocking",
          "All keep running; they start when the parent next blocks "
          "(or ends)"]],
        widths=[20, 42, 38], bold_first=True)
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  task automatic job(string name, int d);',
        '    #d $display("[%0t] %s done (took %0d)", $time, name, d);',
        '  endtask',
        '  initial begin',
        '    $display("-- join: wait for ALL children");',
        '    fork job("A", 10); job("B", 30); job("C", 20); join',
        '    $display("[%0t] after join", $time);',
        '',
        '    $display("-- join_any: wait for the FIRST child; others keep running");',
        '    fork job("D", 10); job("E", 30); join_any',
        '    $display("[%0t] after join_any", $time);',
        '',
        '    $display("-- join_none: do not wait at all");',
        '    fork job("F", 5); join_none',
        '    $display("[%0t] after join_none", $time);',
        '    wait fork;                          // wait for E and F (all children of this thread)',
        '    $display("[%0t] after wait fork", $time);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c20_fork.sv - the three join variants and wait fork.")
    out([
        '-- join: wait for ALL children',
        '[10] A done (took 10)',
        '[20] C done (took 20)',
        '[30] B done (took 30)',
        '[30] after join',
        '-- join_any: wait for the FIRST child; others keep running',
        '[40] D done (took 10)',
        '[40] after join_any',
        '-- join_none: do not wait at all',
        '[40] after join_none',
        '[45] F done (took 5)',
        '[60] E done (took 30)',
        '[60] after wait fork',
        '- top.sv:20: Verilog $finish'],
        "Verilator 5.020 output (Icarus Verilog 12 prints the same lines).")
    bul(["After `join_any` the parent resumed at 40 while E was still "
         "running; E completed at 60, long after the fork statement "
         "'ended'. Leftover children are the source of many end-of-test "
         "bugs.",
         "With `join_none`, the child F did not start at the `fork`: a "
         "`join_none` child is **scheduled**, and runs only when the parent "
         "thread blocks or terminates. That detail is what makes the "
         "loop-variable bug below possible.",
         "`wait fork` blocks until all **immediate** child processes of "
         "the current process have finished - not their own descendants, "
         "and not unrelated threads. Here those were E and F."])

    h2("The classic loop-variable bug")
    p("The most famous fork pitfall: spawning one thread per loop "
      "iteration with `join_none`, and letting each thread use the loop "
      "variable.")
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  int i;                                // ONE static variable shared by every thread',
        '  initial begin',
        '    for (i = 0; i < 3; i++)',
        '      fork',
        '        #1 $display("[%0t] child sees i=%0d", $time, i);',
        '      join_none',
        '    $display("[%0t] loop finished, i=%0d", $time, i);',
        '    #5 $finish;',
        '  end',
        'endmodule'],
         "c20_loopbug.sv - threads that read a shared variable after the "
         "loop has finished.")
    out([
        '[0] loop finished, i=3',
        '[1] child sees i=3',
        '[1] child sees i=3',
        '[1] child sees i=3',
        'c20_loopbug.sv:10: $finish called at 5 (1ns)'], "Icarus Verilog 12 output: the "
        "IEEE-1800 behaviour.")
    p("The loop spawns three children but none of them runs until the "
      "parent blocks at `#5`, by which time the loop has finished and "
      "`i == 3`. All three children read the **same** static variable, so "
      "all see 3. The same happens with `for (int i ...)` in a static "
      "context: the LRM makes the loop variable a single variable of the "
      "loop, not one per iteration.")
    box("warn", "Verilator 5.020 hides this bug",
        "Compiled with Verilator 5.020, the very same file printed "
        "'child sees i=0', 'i=1', 'i=2' - Verilator captured the value of "
        "`i` when each child was created, which is not IEEE 1800 "
        "behaviour. A testbench that 'works' on Verilator can therefore "
        "fail on Questa, VCS or Xcelium. When porting testbenches between "
        "simulators, fork-in-loop code is the first place to review.")
    p("The fix is to give every child its **own automatic copy**, made "
      "while the loop variable still holds the right value, i.e. before "
      "the parent moves on:")
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  initial begin',
        '    for (int i = 0; i < 3; i++) begin',
        '      automatic int k = i;              // a NEW variable per iteration, set BEFORE the fork',
        '      fork',
        '        #1 $display("[%0t] child sees k=%0d", $time, k);',
        '      join_none',
        '    end',
        '    wait fork;                          // wait for all three children',
        '    $display("[%0t] all children done", $time);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c20_loopfix.sv - one automatic variable per iteration.")
    out([
        '[1] child sees k=0',
        '[1] child sees k=1',
        '[1] child sees k=2',
        '[1] all children done',
        '- top.sv:12: Verilog $finish'], "Verilator 5.020 output.")
    p("An `automatic` variable declared in a `begin...end` block is "
      "created afresh each time the block is entered, i.e. once per "
      "iteration, and the child's reference keeps it alive after the "
      "iteration ends. An equivalent, LRM-sanctioned form declares the "
      "copy in the **declaration part of the fork itself** - "
      "`fork automatic int k = i; ... join_none` - because such fork "
      "declarations are initialized when the fork statement executes, "
      "before any child is spawned. (Verilator 5.020 failed with a C++ "
      "compilation error on that second form in our test, so the listing "
      "uses the first.) In a class method or `automatic` task everything "
      "is automatic already, and the explicit copy is still needed "
      "because the loop variable itself is still shared.")

    h2("wait fork, disable fork and their scope")
    p("`disable fork` terminates **all active child processes of the "
      "calling process**, together with their descendants. It is the "
      "standard companion of `join_any`: race a response against a "
      "timeout, continue on whichever comes first, then kill the loser. "
      "The pitfall is the word __all__: children forked earlier by the "
      "same thread, for completely different purposes, die too.")
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  initial begin',
        '    fork                                // background monitor started EARLIER',
        '      forever #20 $display("[%0t]   heartbeat", $time);',
        '    join_none',
        '    fork                                // later: a timeout race in the SAME thread',
        '      #25 $display("[%0t] response arrived", $time);',
        '      #50 $display("[%0t] TIMEOUT", $time);',
        '    join_any',
        '    disable fork;                       // PITFALL: also kills the heartbeat!',
        '    #60 $display("[%0t] no heartbeat since 20", $time);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c20_disable_bug.sv - disable fork also kills an unrelated "
         "background thread.")
    out([
        '[20]   heartbeat',
        '[25] response arrived',
        '[85] no heartbeat since 20',
        '- top.sv:13: Verilog $finish'], "Verilator 5.020 output.")
    p("The heartbeat stopped after 20 ns, because it was a child of the "
      "same `initial` process. The robust pattern wraps the race in an "
      "extra `fork begin ... end join`, so that the thread executing "
      "`disable fork` is a fresh one whose only children are the two "
      "racing branches:")
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  bit timed_out;',
        '  initial begin',
        '    fork                                // background thread started EARLIER',
        '      forever #20 $display("[%0t]   heartbeat", $time);',
        '    join_none',
        "    // Guard the race in its own thread: 'disable fork' then only sees ITS children",
        '    fork begin : guarded',
        '      fork',
        '        begin #25 timed_out = 0; $display("[%0t] response arrived", $time); end',
        '        begin #50 timed_out = 1; $display("[%0t] TIMEOUT", $time); end',
        '      join_any',
        '      disable fork;                     // kills the timeout thread only',
        '    end join',
        '    $display("[%0t] timed_out=%0b", $time, timed_out);',
        '    #50 $display("[%0t] no TIMEOUT at 50, heartbeat still alive", $time);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c20_disable.sv - guarding disable fork with an isolating "
         "fork...join.")
    out([
        '[20]   heartbeat',
        '[25] response arrived',
        '[25] timed_out=0',
        '[40]   heartbeat',
        '[60]   heartbeat',
        '[75] no TIMEOUT at 50, heartbeat still alive',
        '- top.sv:18: Verilog $finish'],
        "Verilator 5.020 output (identical under Icarus Verilog 12).")
    box("warn", "disable <block_name> is static and global",
        "The Verilog `disable label;` statement kills **every** active "
        "execution of the named block, in every thread - if ten drivers "
        "run the same task, `disable` on a block inside it stops all ten. "
        "It predates dynamic processes and does not know which thread you "
        "meant. In class-based code use `disable fork` (with the guard "
        "above) or the `process` class instead.")

    h2("The process class")
    p("`process` is a built-in class (declared in the `std` package; it "
      "cannot be extended or constructed with `new`) that gives a handle "
      "to a running thread. A thread obtains its own handle with the "
      "static function `process::self()` and can hand it to others.")
    tbl(["Method", "Meaning"],
        [["`process::self()`", "Handle to the calling process"],
         ["`status()`", "Enum `process::state`: RUNNING, WAITING, SUSPENDED, "
          "FINISHED, KILLED"],
         ["`kill()`", "Terminate the process and all its descendants"],
         ["`await()`", "Block until that (other) process finishes or is "
          "killed; a process may not await itself"],
         ["`suspend()` / `resume()`", "Pause and continue it"],
         ["`srandom()`, `get_randstate()`, `set_randstate()`",
          "Control the thread's random generator (Chapter 19)"]],
        widths=[35, 65], bold_first=True)
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  process p[3];',
        '  initial begin',
        '    fork                                // each child records its own handle first',
        '      begin p[0] = process::self(); #10 $display("[%0t] worker 0 finished", $time); end',
        '      begin p[1] = process::self(); #20 $display("[%0t] worker 1 finished", $time); end',
        '      begin p[2] = process::self(); #30 $display("[%0t] worker 2 finished", $time); end',
        '    join_none',
        '    #15;',
        '    foreach (p[n]) $display("[%0t] worker %0d status=%s", $time, n, p[n].status().name());',
        '    p[2].kill();                        // terminate worker 2 (and its children)',
        '    p[1].await();                       // block until worker 1 finishes',
        '    $display("[%0t] after await: w1=%s w2=%s", $time,',
        '             p[1].status().name(), p[2].status().name());',
        '    #20 $display("[%0t] worker 2 never printed", $time);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c20_proc.sv - recording process handles, querying status, kill "
         "and await.")
    out([
        '[10] worker 0 finished',
        '[15] worker 0 status=FINISHED',
        '[15] worker 1 status=WAITING',
        '[15] worker 2 status=WAITING',
        '[20] worker 1 finished',
        '[20] after await: w1=FINISHED w2=KILLED',
        '[40] worker 2 never printed',
        '- top.sv:17: Verilog $finish'], "Verilator 5.020 output.")
    p("At 15 ns worker 0 has finished and the others are WAITING (blocked "
      "on their delays). Killing worker 2 removes it before it can print; "
      "`await` returned exactly when worker 1 finished at 20. UVM uses "
      "`process` internally to kill the `run_phase` threads of all "
      "components when the phase ends, and to implement sequence "
      "`kill()`.")

    h2("Named events")
    p("An `event` is a synchronization object with no value. `-> ev` "
      "**triggers** it, unblocking every process currently waiting with "
      "`@ev`. Three details make events subtle:")
    bul(["`@ev` is **edge-sensitive**: it waits for a trigger that happens "
         "__after__ the wait begins. A process that reaches `@ev` in the "
         "same time step but just after the trigger misses it and may "
         "wait forever.",
         "`ev.triggered` is a **level** that stays true from the trigger "
         "until the end of the current time step. `wait (ev.triggered)` "
         "therefore succeeds whether it executes before or after the "
         "trigger within that time step - the standard cure for the race.",
         "`->> ev` is the **nonblocking trigger**: the trigger is "
         "scheduled in the NBA region of the time step, after all active "
         "processes (including ones about to wait) have run. Events can "
         "also be assigned (`ev_a = ev_b` merges them), compared, and set "
         "to `null`; `wait_order(a, b, c)` waits for triggers in a given "
         "order."])
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  event done;',
        '  initial begin                         // waiter 1: edge-sensitive @, waiting early',
        '    @done $display("[%0t] waiter @done woke up", $time);',
        '  end',
        '  initial begin                         // triggers at t=10',
        '    #10 -> done;',
        '    $display("[%0t] triggered done", $time);',
        '  end',
        '  initial begin                         // waiter 2: arrives in the SAME time step, too late',
        '    #10 @done $display("[%0t] late @done woke up (never printed)", $time);',
        '  end',
        '  initial begin                         // waiter 3: level-sensitive triggered state',
        '    #10 wait (done.triggered) $display("[%0t] wait(done.triggered) woke up", $time);',
        '  end',
        '  initial #50 $display("[%0t] end of test", $time);',
        'endmodule'],
         "c20_event.sv - an early waiter, a late waiter and a "
         "wait(triggered) waiter, all in the trigger's time step.")
    out([
        '[10] triggered done',
        '[10] wait(done.triggered) woke up',
        '[10] waiter @done woke up',
        '[50] end of test'], "Verilator 5.020 output.")
    p("Waiters 2 and 3 and the triggering process are all ready at 10 ns "
      "and run in an unspecified order. The run shows the dangerous case: "
      "the trigger ran first, so waiter 2's `@done` started __after__ the "
      "trigger and never woke (its message never appears), while waiter "
      "3's `wait (done.triggered)` succeeded. On another simulator the "
      "order may differ and waiter 2 might wake - which is exactly why the "
      "code is wrong: its behaviour depends on scheduling order. Always "
      "use `wait (ev.triggered)` when the waiter might arrive in the same "
      "time step as the trigger.")

    h2("Semaphores")
    p("A `semaphore` is a built-in class holding a bucket of **keys**. "
      "`new(n)` creates it with n keys (default 0); `get(k)` removes k keys, "
      "blocking until enough are available; `put(k)` returns keys; "
      "`try_get(k)` takes them only if available, returning a positive "
      "value on success and 0 otherwise, without blocking. With one key it "
      "is a **mutex** that serializes access to a shared resource: a bus "
      "that several masters' drivers use, a shared memory model, a log "
      "file.")
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  semaphore bus = new(1);               // one key: a mutex for a shared bus',
        '  task automatic master(int id, int n_cycles);',
        '    bus.get(1);                         // blocks until a key is available',
        '    $display("[%0t] M%0d owns the bus", $time, id);',
        '    #(n_cycles);',
        '    $display("[%0t] M%0d releases", $time, id);',
        '    bus.put(1);                         // return the key',
        '  endtask',
        '  initial begin',
        '    fork',
        '      master(0, 10);',
        '      master(1, 5);',
        '      begin',
        '        #1 if (!bus.try_get(1)) $display("[%0t] M2 try_get failed, not blocking", $time);',
        '      end',
        '    join',
        '    $finish;',
        '  end',
        'endmodule'],
         "c20_sem.sv - a one-key semaphore arbitrating a bus between "
         "masters.")
    out([
        '[0] M0 owns the bus',
        '[1] M2 try_get failed, not blocking',
        '[10] M0 releases',
        '[10] M1 owns the bus',
        '[15] M1 releases',
        '- top.sv:19: Verilog $finish'], "Verilator 5.020 output.")
    bul(["M0 and M1 both called `get` at time 0; M0 won, M1 blocked until "
         "M0's `put` at 10. The LRM specifies that waiting `get` requests "
         "are served in FIFO order, but which of two same-time callers "
         "queues first is scheduling order.",
         "`put` does not check ownership: any thread may put keys, and "
         "putting more keys than were taken silently grows the bucket. "
         "Always pair get/put in the same task, and put in every exit path.",
         "Forgetting a `put` (for example after an early `return` or a "
         "`disable fork` that kills the owner) deadlocks every later user - "
         "a common cause of simulations that 'hang' until a watchdog fires."])

    h2("Mailboxes")
    p("A `mailbox` is a built-in FIFO for passing messages between "
      "processes - the SystemVerilog equivalent of a channel. It is the "
      "natural connection between a generator and a driver, or a monitor "
      "and a scoreboard.")
    tbl(["Method", "Blocking?", "Behaviour"],
        [["`new(bound = 0)`", "-", "0 = unbounded; >0 = capacity"],
         ["`put(msg)`", "Yes, when full", "Append to the tail"],
         ["`try_put(msg)`", "No", "Returns 1 if stored, 0 if full"],
         ["`get(ref msg)`", "Yes, when empty", "Remove the head"],
         ["`try_get(ref msg)`", "No", "Returns >0 if a message was "
          "removed, 0 if empty (negative on type mismatch)"],
         ["`peek(ref msg)`", "Yes, when empty", "Copy the head without "
          "removing it"],
         ["`try_peek(ref msg)`", "No", "As peek, returns 0 if empty"],
         ["`num()`", "No", "Number of messages currently stored"]],
        widths=[25, 20, 55], bold_first=True)
    p("A **parameterized** mailbox, `mailbox #(Txn)`, accepts only that "
      "type and is checked at compile time. A plain `mailbox` is typeless: "
      "it accepts anything, and a `get` into a variable of the wrong type "
      "is a **run-time** error. Always use the parameterized form.")
    code([
        '`timescale 1ns/1ns',
        'class Txn;',
        '  int id; bit [7:0] data;',
        "  function new(int id); this.id = id; data = 8'(id * 17); endfunction",
        'endclass',
        '',
        'module top;',
        '  mailbox #(Txn) mb = new(2);           // parameterized, BOUNDED to 2 entries',
        '  initial begin : producer',
        '    for (int n = 0; n < 4; n++) begin',
        '      automatic Txn t = new(n);         // automatic: a fresh handle per iteration',
        '      mb.put(t);                        // blocks while the mailbox is full',
        '      $display("[%0t] put   id=%0d  (num=%0d)", $time, n, mb.num());',
        '    end',
        '  end',
        '  initial begin : consumer',
        '    Txn t;',
        '    #10;                                // start late: the producer fills up and blocks',
        '    mb.peek(t);                         // look without removing',
        '    $display("[%0t] peek  id=%0d  (num=%0d)", $time, t.id, mb.num());',
        '    repeat (4) begin',
        '      mb.get(t);                        // blocks while the mailbox is empty',
        '      $display("[%0t] get   id=%0d data=%0d", $time, t.id, t.data);',
        '      #5;',
        '    end',
        '    if (mb.try_get(t) == 0) $display("[%0t] try_get on empty mailbox returns 0", $time);',
        '    $finish;',
        '  end',
        'endmodule'],
         "c20_mbox.sv - producer and consumer connected by a bounded, "
         "parameterized mailbox.")
    out([
        '[0] put   id=0  (num=1)',
        '[0] put   id=1  (num=2)',
        '[10] peek  id=0  (num=2)',
        '[10] get   id=0 data=0',
        '[10] put   id=2  (num=2)',
        '[15] get   id=1 data=17',
        '[15] put   id=3  (num=2)',
        '[20] get   id=2 data=34',
        '[25] get   id=3 data=51',
        '[30] try_get on empty mailbox returns 0',
        '- top.sv:27: Verilog $finish'], "Verilator 5.020 output.")
    p("The bound of 2 gives **back-pressure**: the producer put ids 0 and 1 "
      "at time 0 and then blocked in `put` until the consumer freed a slot "
      "at 10; from then on, the two threads advance in lock-step with the "
      "consumer's rate. An unbounded mailbox would have let the producer "
      "run arbitrarily far ahead, which is sometimes what you want "
      "(monitor to scoreboard) and sometimes a problem (a generator that "
      "creates a million transactions before the driver sends one).")
    box("warn", "A mailbox stores handles, not copies",
        "`mb.put(t)` stores the **handle** `t`. If the producer then "
        "modifies the same object and puts it again, the consumer receives "
        "two handles to one object whose contents are whatever the producer "
        "wrote last. The producer above constructs a new Txn per iteration "
        "(and declares `t` `automatic` so that each iteration really has "
        "its own variable: a declaration with an initializer inside a loop "
        "of a static block would otherwise be a static variable, "
        "initialized only once). Copy-on-send or "
        "new-per-transaction is mandatory.")

    h3("Choosing a synchronization primitive")
    tbl(["Need", "Use", "UVM equivalent"],
        [["Signal 'something happened', no data", "event, `wait(ev.triggered)`",
          "`uvm_event`, objections for end of test"],
         ["Mutual exclusion / limited resource", "semaphore",
          "Sequencer arbitration, `lock()`/`grab()`"],
         ["Pass transactions with flow control", "mailbox (bounded)",
          "`uvm_tlm_fifo`, `seq_item_port` get/put"],
         ["Broadcast transactions to many", "Loop over mailboxes, or "
          "callbacks", "`uvm_analysis_port` (write to all subscribers)"],
         ["Wait for a set of threads", "`fork...join`, `wait fork`",
          "`uvm_objection` drop / `phase_ready_to_end`"]],
        widths=[33, 32, 35], bold_first=True)
    box("expert", "Interview favourites",
        "(1) 'Print 0..9 from ten join_none threads' - automatic copy per "
        "iteration. (2) 'Difference between @ev and wait(ev.triggered)' - "
        "edge vs level within the time step. (3) 'Implement a mailbox with "
        "a semaphore and a queue' - two semaphores (slots and items) plus "
        "a queue. (4) 'What does disable fork kill?' - all children of the "
        "current process, including unrelated earlier ones; isolate with "
        "fork begin ... end join. (5) 'Can a function contain fork?' - only "
        "`fork...join_none`, because a function must not block.")

    h2("Summary")
    bul(["`join` waits for all children, `join_any` for the first, "
         "`join_none` for none; `join_none` children start only when the "
         "parent blocks.",
         "Threads spawned in a loop must use a per-iteration automatic "
         "copy of the loop variable; Verilator 5.020 masks this bug, IEEE "
         "simulators expose it.",
         "`wait fork` waits for all immediate children; `disable fork` kills "
         "**all** descendants of the current process; isolate with an extra "
         "fork...join.",
         "The `process` class exposes self, status, kill, await, suspend "
         "and resume.",
         "Events: `->` triggers, `@` is edge-sensitive, `.triggered` is a "
         "level for the rest of the time step, `->>` triggers in the NBA "
         "region.",
         "Semaphores serialize access with keys (get/put/try_get); "
         "mailboxes pass typed messages with optional bound and "
         "back-pressure (put/get/peek/try_*/num).",
         "Mailboxes pass handles: construct a new object per message."])

    h2("Exercises")
    bul(["Rewrite `c20_loopbug.sv` so that each child prints its index "
         "using the fork-declaration form `fork automatic int k = i; ... "
         "join_none`, and run it on a simulator that accepts it.",
         "Write a task `with_timeout(int ns)` that runs a transaction task "
         "and reports an error if it takes longer than `ns`, without "
         "killing any other thread of the caller.",
         "Build a bounded mailbox yourself from a queue and two semaphores "
         "and verify that it behaves like `c20_mbox.sv`.",
         "Modify `c20_sem.sv` so that masters need 2 of 3 keys. Which "
         "masters can overlap, and what happens if one master calls "
         "`get(4)`?",
         "Create a monitor thread that triggers an event on every "
         "transaction and a checker that uses `@`. Construct a case in "
         "which the checker misses a transaction, then fix it.",
         "Explain why a function may contain `fork...join_none` but not "
         "`fork...join`, and give a real use for the former."],
        ordered=True)


# =============================================================================
#            Chapter 21 - Clocking blocks, program blocks, race-free TBs
# =============================================================================
def ch21():
    chapter("Clocking Blocks, Program Blocks and Race-Free Testbenches")
    p("A testbench and a DUT that both react to the same clock edge are two "
      "groups of processes woken in the same time step. If the testbench "
      "writes an input with a blocking assignment at `@(posedge clk)`, "
      "whether the DUT's flip-flops see the old or the new value depends on "
      "which process the simulator happens to run first - a **race**. "
      "Races are the most expensive testbench bugs: the test passes on one "
      "simulator, fails on another, and changes behaviour when an unrelated "
      "line is added. This chapter explains the complete SystemVerilog "
      "scheduling algorithm, then the two language features designed to "
      "remove TB-DUT races by construction - **clocking blocks** and "
      "**program blocks** - and the housekeeping constructs every "
      "testbench uses: `final`, `$exit`, `timeunit` and `timeprecision`.")

    h2("Anatomy of a race")
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  logic clk = 0, d = 0, q1, q2;',
        '  always #5 clk = ~clk;',
        '  always @(posedge clk) q1 <= d;          // "DUT" flop 1: declared BEFORE the stimulus',
        '  initial begin                           // stimulus with a BLOCKING write at the edge',
        '    @(posedge clk) d = 1;                 // RACE: same region as the flops',
        '    @(posedge clk) d = 0;',
        '    #1 $finish;',
        '  end',
        '  always @(posedge clk) q2 <= d;          // "DUT" flop 2: declared AFTER the stimulus',
        '  always @(negedge clk) $display("[%0t] d=%b q1=%b q2=%b", $time, d, q1, q2);',
        'endmodule'],
         "c21_race.sv - stimulus written with a blocking assignment at the "
         "clock edge.")
    out([
        '[10] d=1 q1=1 q2=0',
        'c21_race.sv:9: $finish called at 16 (1ns)'], "Icarus Verilog 12 output.")
    p("Both flip-flops are identical and sample the same `d` at the same "
      "edge, yet at 10 ns they disagree: `q1` caught the new value and "
      "`q2` the old one. At the edge, three processes are ready in the "
      "Active region - flop 1, flop 2 and the stimulus - and the LRM lets "
      "the simulator run them in any order. Icarus happened to run flop 2 "
      "before the stimulus and flop 1 after it. Another simulator, another "
      "version, or a reordered source file gives a different answer. "
      "(Verilator 5.020 printed `q1=1 q2=1` for this file.) Real "
      "hardware has no such ambiguity: a flop samples its input just "
      "before the edge. The goal of every technique in this chapter is to "
      "make the testbench behave like that hardware.")

    h2("The SystemVerilog scheduling regions")
    p("Chapter 5 introduced the Verilog event queue (Active, Inactive, NBA, "
      "Monitor). IEEE 1800 refines each **time slot** into a fixed sequence "
      "of regions, adding a sampling region before everything, an Observed "
      "region for assertions, and a mirror-image **reactive** region set "
      "for testbench code. The PLI-only regions (Pre-Active, Pre-NBA, "
      "Post-NBA, Pre-Observed, Post-Observed, Pre-Re-NBA, Post-Re-NBA, "
      "Pre-Postponed) are omitted from the figure; they exist for VPI "
      "callbacks.")
    diagram([
        "  time slot t",
        "  +---------------------------------------------------------------+",
        "  | PREPONED   sample #1step inputs, assertion/coverage values    |",
        "  +---------------------------------------------------------------+",
        "      |",
        "      v             ACTIVE REGION SET (design: modules, interfaces)",
        "  +---------------------------------------------------------------+",
        "  | ACTIVE     always/initial in modules, assign, blocking =,     |<-+",
        "  |            RHS of <=, $display, gate evaluation              |  |",
        "  | INACTIVE   processes resumed after #0                        |  |",
        "  | NBA        nonblocking-assignment updates (LHS of <=)        |--+",
        "  +---------------------------------------------------------------+",
        "      |  (loop until Active, Inactive and NBA are all empty)",
        "      v",
        "  +---------------------------------------------------------------+",
        "  | OBSERVED   concurrent assertions evaluated (on sampled values) |",
        "  +---------------------------------------------------------------+",
        "      |             REACTIVE REGION SET (testbench: programs)",
        "      v",
        "  +---------------------------------------------------------------+",
        "  | REACTIVE   program code, assertion action blocks             |<-+",
        "  | RE-INACTIVE  #0 inside programs                              |  |",
        "  | RE-NBA     <= updates from programs, clocking #0 drives      |--+",
        "  +---------------------------------------------------------------+",
        "      |  (if anything scheduled Active events: back to ACTIVE)",
        "      v",
        "  +---------------------------------------------------------------+",
        "  | POSTPONED  $strobe, $monitor, read-only; then advance time    |",
        "  +---------------------------------------------------------------+",
    ], "The IEEE 1800 time slot. Design code iterates in the active set; "
       "testbench code in the reactive set runs after the design has "
       "settled; everything re-iterates until no events remain in the "
       "time slot.")
    tbl(["Region", "What executes there", "Why it matters"],
        [["Preponed", "Sampling for `#1step` clocking inputs and for "
          "concurrent assertions and coverage", "Values 'just before' the "
          "edge, immune to races"],
         ["Active", "Module processes, continuous assignments, blocking "
          "assignments, RHS of `<=`", "Order within the region is "
          "undefined"],
         ["Inactive", "Threads resumed from `#0`", "`#0` is a hack for "
          "ordering; avoid it"],
         ["NBA", "LHS updates of `<=` from module code", "Makes flops "
          "order-independent"],
         ["Observed", "Evaluation of concurrent assertions (Chapter 22)",
          "Uses Preponed samples"],
         ["Reactive", "Program processes, assertion pass/fail action "
          "blocks", "Testbench reacts after design settled"],
         ["Re-Inactive / Re-NBA", "`#0` and `<=` in program code; "
          "clocking-block drives with `#0` output skew",
          "Mirror of Inactive/NBA for the TB"],
         ["Postponed", "`$strobe`, `$monitor`, final sampling",
          "Sees the final values of the time slot; nothing may change them"]],
        widths=[16, 47, 37], bold_first=True)
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  int a = 0;',
        '  initial begin',
        '    #10;',
        '    a = 1;                                          // Active: immediate update',
        '    a <= 2;                                         // NBA: update scheduled for later',
        '    $strobe ("[%0t] $strobe  (Postponed) a=%0d", $time, a);',
        '    $display("[%0t] $display (Active)    a=%0d", $time, a);',
        '    #0 $display("[%0t] after #0 (Inactive) a=%0d", $time, a);',
        '    #1 $display("[%0t] next time step     a=%0d", $time, a);',
        '  end',
        'endmodule'],
         "c21_regions.sv - which value each kind of statement sees.")
    out([
        '[10] $display (Active)    a=1',
        '[10] after #0 (Inactive) a=1',
        '[10] $strobe  (Postponed) a=2',
        '[11] next time step     a=2'], "Icarus Verilog 12 output.")
    p("`$display` executes immediately in Active and sees the blocking "
      "value 1; the process resumed from `#0` runs in Inactive, which comes "
      "**before** NBA, so it still sees 1; the NBA update to 2 happens "
      "next, and `$strobe` prints in Postponed, after all updates. The "
      "same file compiled with Verilator 5.020 printed `a=2` for all "
      "three lines of time 10: Verilator does not implement the "
      "Active/Inactive/NBA distinction inside `initial` blocks as the LRM "
      "does. Use an event-driven simulator (Icarus, or any commercial one) "
      "to reason about regions.")
    p("With the regions in hand, the classic fix for the race is clear: "
      "drive DUT inputs with **nonblocking** assignments, so the new value "
      "is written in NBA, after every flop has read the old one in Active.")
    code([
        '  initial begin                           // stimulus with a NONBLOCKING write at the edge',
        '    @(posedge clk) d <= 1;                // NBA: flops sampled the OLD d',
        '    @(posedge clk) d <= 0;'],
         "c21_norace.sv - the only change to c21_race.sv.")
    out([
        '[10] d=1 q1=0 q2=0',
        'c21_norace.sv:9: $finish called at 16 (1ns)'], "Icarus Verilog 12 output: both flops agree.")
    p("Nonblocking stimulus removes the race on **inputs**, but a testbench "
      "that __samples__ DUT outputs at `@(posedge clk)` still races with "
      "the NBA updates of those outputs, and every engineer must remember "
      "the discipline. Clocking blocks move the discipline into the "
      "language.")

    h2("Clocking blocks")
    p("A **clocking block** declares, for one clock, which signals a "
      "testbench samples (`input`), which it drives (`output`, `inout`), "
      "and **when**: an input is sampled a given **skew** before the "
      "clocking event, and an output is driven a given skew after it. "
      "The testbench then reads `cb.sig` and writes `cb.sig <= value` "
      "instead of touching the raw signals, and is automatically "
      "synchronized to the clock like the flip-flops around it.")
    code([
        'module dut (input logic clk, rst_n, input logic [7:0] d, output logic [7:0] q);',
        '  always_ff @(posedge clk or negedge rst_n)',
        '    if (!rst_n) q <= \'0; else q <= d + 8\'d1;     // registered "increment"',
        'endmodule',
        '',
        'module top;',
        '  timeunit 1ns; timeprecision 100ps;',
        '  logic clk = 0, rst_n = 0;',
        '  logic [7:0] d = 0, q;',
        '  always #5 clk = ~clk;                          // posedges at 5, 15, 25, ...',
        '  dut u (.*);',
        '',
        "  default clocking cb @(posedge clk);            // 'default' enables ##n delays",
        '    default input #1step output #2;              // sample just before edge, drive 2ns after',
        '    output d, rst_n;',
        '    input  q;',
        '  endclocking',
        '',
        '  initial begin',
        '    ##1 cb.rst_n <= 1;                           // clocking drive (always nonblocking)',
        '    for (int n = 10; n < 13; n++) begin',
        "      ##1 cb.d <= 8'(n);",
        '      $display("[%4.1f] edge: cb.q=%0d q=%0d; drive d=%0d", $realtime, cb.q, q, n);',
        '    end',
        '    repeat (2) begin',
        '      ##1;                                       // wait one clock cycle',
        '      $display("[%4.1f] edge: cb.q=%0d q=%0d", $realtime, cb.q, q);',
        '    end',
        '    $finish;',
        '  end',
        '  always @(d) $display("[%4.1f]   pin d <- %0d", $realtime, d);',
        'endmodule'],
         "c21_cb.sv - a default clocking block with #1step input and #2 "
         "output skews, ##n cycle delays, and clocking drives.")
    out([
        '[ 0.0]   pin d <- 0',
        '[15.0] edge: cb.q=0 q=0; drive d=10',
        '[17.0]   pin d <- 10',
        '[25.0] edge: cb.q=1 q=1; drive d=11',
        '[27.0]   pin d <- 11',
        '[35.0] edge: cb.q=11 q=11; drive d=12',
        '[37.0]   pin d <- 12',
        '[45.0] edge: cb.q=12 q=12',
        '[55.0] edge: cb.q=13 q=13',
        '- top.sv:29: Verilog $finish'], "Verilator 5.020 output.")
    p("Walk through the timeline. At each edge the testbench reads "
      "`cb.q`, which is the value of `q` sampled in the **Preponed** region "
      "of that time slot (`#1step`) - the value a real flop would capture. "
      "`cb.d <= n` does not change `d` now: it schedules the drive for this "
      "clocking event plus the output skew, so `d` changes at 17, 27, 37, "
      "exactly 2 ns after each edge, well clear of the edge in both "
      "directions. The DUT registers `d + 1`, so the value sampled at edge "
      "N is what the DUT computed at edge N-1: `cb.q` becomes 11 at 35 "
      "because the DUT captured `d = 10` at 25. The testbench sees "
      "exactly the waveform a logic analyser would show.")
    tbl(["Syntax", "Meaning"],
        [["`clocking cb @(posedge clk); ... endclocking`",
          "Named clocking block; the event can be any event expression"],
         ["`default input #1step output #2;`", "Default skews for the block"],
         ["`input #1step`", "Sample in the Preponed region: value just "
          "before the edge (default input skew)"],
         ["`input #0`", "Sample in the **Observed** region of the edge's "
          "time slot (after the design settled - rarely what you want)"],
         ["`input #3ns` / `output #2`", "Explicit time skews (in the "
          "block's time unit when unitless)"],
         ["`output #0` (default output skew)", "Drive in the Re-NBA region "
          "of the edge's time slot"],
         ["`output negedge`", "Skew given as an edge of the clock"],
         ["`default clocking cb ...;`", "One per module/interface/program; "
          "enables `##n` and is the default for assertions"],
         ["`##n`", "Wait n clocking events of the default clocking"],
         ["`@(cb)`", "Wait for the clocking event itself"],
         ["`cb.sig <= expr;` / `cb.sig <= ##2 expr;`", "Synchronous drive, "
          "optionally n cycles later; `=` is illegal on clocking outputs"],
         ["`global clocking`", "Names the primary system clock for "
          "formal/assertions (`$global_clock`, Chapter 22)"]],
        widths=[42, 58], bold_first=True,
        caption="Clocking block syntax and semantics.")
    bul(["A clocking block does not create signals; `cb.q` is a view of "
         "`q`. Reading `q` directly bypasses the sampling (the example "
         "prints both; they agree only because the display runs before the "
         "NBA update of that slot).",
         "Clocking blocks are declared inside modules, interfaces or "
         "programs; in UVM they live in the **interface**, and the driver "
         "and monitor reach them through a virtual interface: "
         "`vif.drv_cb.valid <= 1; @(vif.drv_cb);` (Chapter 16 shows how "
         "`modport` exports them).",
         "Several clocking blocks may use the same clock with different "
         "directions and skews - typically `drv_cb` and `mon_cb` in one "
         "interface.",
         "Inputs and outputs of a clocking block can be hierarchical "
         "expressions: `input en = top.dut.u_ctrl.en;`."])
    box("warn", "Tool portability: clocking-block corner cases",
        "Verilator 5.020 rejected the two-step form `clocking cb ...; ... "
        "default clocking cb;` ('Unsupported: default clocking "
        "identifier'), so the listing uses `default clocking cb @(...)` "
        "directly. In an earlier version of this example, an `@(cb)` "
        "executed right after a `##1` in the same time step resumed "
        "**in that same time step** on Verilator and read post-NBA values; "
        "the LRM says it must wait for the next clocking event. Commercial "
        "simulators follow the LRM here, but mixing `@(cb)`, `##n` and raw "
        "`@(posedge clk)` in one thread is a known source of off-by-one-"
        "cycle bugs on every tool: pick one style per driver.")

    h2("Program blocks")
    p("A **program** is a module-like container for testbench code whose "
      "processes run in the **Reactive** region set. Because reactive "
      "code runs only after the design's active set has settled, a "
      "program can read DUT outputs and even write DUT inputs with "
      "blocking assignments at the clock edge without racing the design. "
      "Program blocks also give an automatic end of simulation.")
    code([
        '`timescale 1ns/1ns',
        'module top;',
        '  logic clk = 0, q;',
        "  wire  d;                                // driven by the program's output port",
        '  int   n_edges;',
        '  always #5 clk = ~clk;',
        '  always @(posedge clk) q <= d;           // DUT flop (design region: Active/NBA)',
        '  always @(posedge clk) n_edges++;',
        '  test t (.clk(clk), .d(d), .q(q));',
        '  final $display("final block: %0d clock edges simulated", n_edges);',
        'endmodule',
        '',
        'program automatic test (input logic clk, output logic d, input logic q);',
        '  initial begin                           // runs in the REACTIVE region set',
        '    d = 0;',
        '    repeat (2) begin',
        '      @(posedge clk);',
        '      d = ~d;                             // even a blocking write cannot race the flop',
        '      $display("[%0t] program: drove d=%b, q=%b", $time, d, q);',
        '    end',
        '    #1 $display("[%0t] program ends -> $exit", $time);',
        '    $exit;                                // ends this program; last program ends the sim',
        '  end',
        'endprogram'],
         "c21_prog.sv - a program driving a module-based design, with "
         "final and $exit.")
    out([
        '[5] program: drove d=1, q=0',
        '[15] program: drove d=0, q=1',
        '[16] program ends -> $exit',
        '- top.sv:22: Verilog $finish',
        'final block: 2 clock edges simulated'], "Verilator 5.020 output.")
    bul(["At 5 ns the program read `q=0`, the flop's value **after** its NBA "
         "update in that slot; the flop had already captured `d=0` before "
         "the program's blocking write, so there is no race even though "
         "`d = ~d` is blocking.",
         "A program may contain `initial` and `final` procedures, data, "
         "classes, tasks, functions, clocking blocks and continuous "
         "assignments. It may **not** contain `always` procedures, module "
         "instances, interfaces or other programs, and it cannot be "
         "instantiated inside a program.",
         "When every `initial` procedure of every program has finished, "
         "the simulation ends as if `$finish` were called. `$exit` ends the "
         "calling program immediately (all of its threads); here that was "
         "the last program, so simulation ended at 16 and ran the `final` "
         "block.",
         "Tasks called from a program run in the reactive region; module "
         "code called from anywhere runs in the caller's region."])
    box("note", "Program blocks in today's industry",
        "Program blocks were introduced with Vera/VMM-style testbenches, and "
        "you will meet them in legacy code and interview questions. Modern "
        "UVM testbenches do **not** use them: UVM's `run_test()` is called "
        "from a module, components are classes, and race-freedom comes from "
        "clocking blocks in interfaces plus nonblocking drives. Programs "
        "also complicate things: a module task called from a program "
        "executes in the reactive region, which surprises code written for "
        "Active-region timing, and a class method executes in the region "
        "of whatever thread calls it. "
        "Verilator 5.020 accepts `program` and `$exit` but does not model "
        "the reactive region set separately, so the run above demonstrates "
        "syntax, not scheduling.")

    h2("final blocks")
    p("A `final` procedure runs once, at the end of simulation - when "
      "`$finish` is called (explicitly, by `$fatal`, or implicitly by the "
      "end of all programs) or when the event queue becomes empty. It "
      "executes in zero time, like a function: no delays, no event "
      "controls, no blocking calls. Multiple final blocks run in an "
      "undefined order. It is the right place for end-of-test reports: "
      "error counts, scoreboard leftovers (expected items never seen), "
      "coverage summaries and 'TEST PASSED/FAILED' lines that regression "
      "scripts grep for. UVM's report phase is the class-based equivalent.")
    box("tip", "End-of-test checks belong in final - but not only there",
        "A scoreboard that still holds expected transactions at the end "
        "means the DUT dropped data. Checking `expected.size() == 0` in "
        "`final` catches it even when the test ended through a timeout or a "
        "`$fatal` elsewhere. But `final` cannot wait for in-flight "
        "transactions to drain; drain first (wait for idle, then a few "
        "cycles), then `$finish`, then let `final` report.")

    h2("timeunit, timeprecision and the timescale directive")
    p("Delays such as `#5` are multiples of the **time unit** of the design "
      "element that contains them, rounded to its **time precision**. "
      "Verilog sets both with the compiler directive `timescale`, which "
      "is a textual, file-order-dependent setting that leaks into every "
      "file compiled after it (Chapter 8). SystemVerilog adds the "
      "`timeunit` and `timeprecision` keywords, which are part of the "
      "module (or interface, program, package, compilation unit) itself.")
    code([
        'module fast;                         // local time unit and precision',
        '  timeunit 1ns;',
        '  timeprecision 100ps;',
        '  initial begin',
        '    #1.26;                           // 1.26 ns rounds to the 100ps precision -> 1.3 ns',
        '    $display("fast: $time=%0d  $realtime=%0.2f (units of 1ns)", $time, $realtime);',
        '    $printtimescale;',
        '  end',
        'endmodule',
        '',
        'module slow;',
        '  timeunit 1us / 1ns;                // combined form: unit / precision',
        '  initial begin',
        '    #0.0025;                         // 2.5 ns -> 3 ns at 1ns precision',
        '    $display("slow: $realtime=%0.4f (units of 1us)", $realtime);',
        '    $printtimescale;',
        '  end',
        'endmodule',
        '',
        'module top;',
        '  timeunit 1ns; timeprecision 1ps;',
        '  fast f(); slow s();',
        '  initial #10 $display("top : $realtime=%0.3f ns", $realtime);',
        'endmodule'],
         "c21_tu.sv - per-module time units, rounding to precision, and "
         "$printtimescale.")
    out([
        'fast: $time=1  $realtime=1.30 (units of 1ns)',
        'Time scale of (top.f) is 1ns / 100ps',
        'slow: $realtime=0.0030 (units of 1us)',
        'Time scale of (top.s) is 1us / 1ns',
        'top : $realtime=10.000 ns'], "Icarus Verilog 12 output.")
    bul(["`#1.26` in a 1ns/100ps module is rounded to 1.3 ns; `$time` "
         "returns the time **rounded to the module's unit** (1), "
         "`$realtime` keeps the fraction (1.30).",
         "`#0.0025` in a 1us/1ns module is 2.5 ns, rounded to 3 ns, and "
         "`$realtime` reports it in microseconds (0.0030).",
         "`timeunit` / `timeprecision` must be the first items in the "
         "design element; the combined form `timeunit 1us / 1ns;` is also "
         "legal. A declaration in the element beats any `timescale` "
         "in effect, which beats a compilation-unit-level declaration, which "
         "beats the tool's default.",
         "The simulator's global time precision is the finest precision of "
         "all design elements, and `#1step` equals one unit of that global "
         "precision.",
         "`$printtimescale` and `$timeformat` (Chapter 10) help debug "
         "timing mismatches. Verilator 5.020 ignored the per-module "
         "`timeprecision` in this example (it printed 1.26 and "
         "'1ns / 1ps'), another reason to use an event-driven simulator for "
         "timing questions."])
    box("warn", "Mixed time units in a testbench",
        "A classic integration bug: an IP's testbench file has no time "
        "declaration and silently inherits a `timescale` of 1ps/1ps from a "
        "file compiled before it, so `#10` becomes 10 ps instead of 10 ns "
        "and the clock runs 1000x faster. Put `timeunit`/`timeprecision` "
        "(or a `timescale`) in **every** file, or use the tool option "
        "that errors on missing time units (most simulators have one).")

    h2("A race-free testbench checklist")
    checklist("Race-free TB-DUT interaction", [
        "Drive DUT inputs through a clocking block (`cb.sig <= v`) or, "
        "without one, with nonblocking assignments.",
        "Sample DUT outputs through a clocking block (`cb.sig`, `#1step`) "
        "or in a monitor that uses the same edge and reads values updated "
        "by NBA only.",
        "Never use `#0` to 'fix' ordering; it moves the race, it does not "
        "remove it.",
        "Generate clocks with a single process; derive other clocks with "
        "nonblocking or in the same process to avoid delta-cycle skew "
        "between clock domains of a synchronous design.",
        "Keep reset release synchronous to the clock (drive it through "
        "the clocking block).",
        "Do not mix `@(posedge clk)`, `@(cb)` and `##n` in one thread.",
        "Use `wait (ev.triggered)` rather than `@ev` for same-time-step "
        "handshakes (Chapter 20).",
        "Put `timeunit`/`timeprecision` in every file; report with `final`.",
        "Confirm race-sensitive behaviour on an event-driven, "
        "LRM-compliant simulator - Verilator deviates in several of the "
        "cases shown in this chapter.",
    ])

    h2("Summary")
    bul(["A race is a result that depends on the undefined order of "
         "processes in one region; TB-DUT races at the clock edge are the "
         "common case.",
         "Each time slot runs Preponed, the active set (Active, Inactive, "
         "NBA), Observed, the reactive set (Reactive, Re-Inactive, Re-NBA) "
         "and Postponed, iterating until no events remain.",
         "Clocking blocks sample inputs a skew before the clock event "
         "(`#1step` = Preponed) and drive outputs a skew after it "
         "(`#0` = Re-NBA); `default clocking` enables `##n`.",
         "Program blocks run TB code in the reactive set and end the "
         "simulation when all their initial blocks finish; `$exit` ends a "
         "program early. UVM uses modules + clocking blocks instead.",
         "`final` blocks run once, in zero time, at the end of simulation.",
         "`timeunit`/`timeprecision` bind time units to the design element; "
         "`#1step` is one global precision unit."])

    h2("Exercises")
    bul(["Add a third flop to `c21_race.sv` that uses `always_ff` and "
         "place it between the other two. Predict whether the result "
         "changes on Icarus, then run it.",
         "Rewrite the stimulus of `c21_race.sv` with a clocking block "
         "(`output #1`) and show that both flops always agree.",
         "In `c21_cb.sv`, change the input skew to `#0` and predict the "
         "sampled values at every edge. Why is `#1step` the default?",
         "Draw the regions in which each statement of `c21_regions.sv` "
         "executes, and predict the output if `a <= 2` is replaced by "
         "`#0 a = 2`.",
         "Write an interface `apb_if` with a `drv_cb` (outputs: psel, "
         "penable, pwrite, paddr, pwdata; inputs: pready, prdata) and a "
         "`mon_cb` (all inputs), plus modports for driver and monitor.",
         "Interview drill: explain in three sentences why a program block "
         "can use blocking assignments to DUT inputs without racing the "
         "DUT, and why UVM testbenches nevertheless do not use programs."],
        ordered=True)
