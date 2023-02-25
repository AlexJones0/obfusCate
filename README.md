
***<img src="app/graphics/icons/logo.png" width="40" height="40"></img> obfusCate*: An automated, approachable C source-to-source obfuscator**
===============

<img src="app/graphics/examples/example1.png"></img>

## **Table of Contents**
----
1. [**Introduction**](#1-introduction)

2. [**Installation**](#2-installation)

3. [**Debugging**](#3-debugging)
    
    3.1. [**Python Installation Issues**](#31-python-installation-issues)
    
    3.2. [**Pip Issues**](#32-pip-issues)

    3.3. [**Clang Issues**](#33-clang-issues)

    3.4. [**Python Script Issues**](#34-python-script-issues)

    3.5. [**Other Issues**](#35-other-issues)

4. [**Usage**](#4-usage)

    4.1. [**Running the Program**](#41-running-the-program)

    4.2. [**Supported Transformations**](#42-supported-transformations)

    4.3. [**Supported Complexity Metrics**](#43-supported-complexity-metrics)

    4.4. [**Other Notable Features**](#44-other-notable-features)

5. [**Project Structure / Documentation**](#5-project-structure--documentation)

    5.1. [**Project Structure**](#51-project-structure)

    5.2. [**Documentation**](#52-documentation)

6. [**Testing**](#6-testing)

    6.1. [**Unit, Integration and System Testing**](#61-unit-integration-and-system-testing)

    6.2 [**Testing Obfuscation Correctness**](#62-testing-obfuscation-correctness)

7. [**Acknowledgements**](#7-acknowledgements)

<br></br>

## **1. Introduction**
----

###
**obfusCate** is a C source-to-source obfuscator, meaning that it takes programs written in the C programming language, and translates them into obfuscated programs also written in the C programming language, which perform the same functionality but are incomprehensible and harder to understand. 

obfusCate aims to provide a complete, whole package that makes C program obfuscation easy and approachable like never before - everyone should be able to secure their code, regardless of their knowledge about compiler and language design and information security! By providing a seamless and responsive GUI interface with flexible, modular obfuscation tools and a whole host of code complexity metrics and helfpul tooltips, we aim to enable *anybody* who wants to obfuscate their code to be able to do so, without having to battle with the interfaces of other complicated tools.

For those that cannot access (or would rather not access) a GUI interface, we also provide a menu-driven CLI interface that should allow users to easily obfuscate their C code. For the power users out there, you can even run the program as a single command-line command if you provide the list of obfuscation transformations to use in JSON format (alongside relevant options, of course). 

###

<br></br>

## **2. Installation**
----
The following steps are all that is needed for installation:

1. Make sure Python 3.8 or later is installed on your system, and is being used by your python path. You can check this using the command 

    ```
    > python3 --version
    ``` 
    
    or perhaps `python --version`, depending on your python setup options. Make note of your python command, and use it from here on. 

2. In the project root directory, run the command

    ``` 
    > py -m pip install -r requirements.txt
    ```

    to install the required python modules. *Hopefully*, installation of the *libclang* module will automatically install clang on your system if it is not already installed. If not, see the [Debugging section](#3-debugging) for possible help.

3. Everything needed to run the project should now be installed! You can see the [Usage section](#4-usage) to see how you are intended to run the program!

*Note:* Alternatively, you can just try running some install scripts I have set up that will try and determine your python executable alias for you - but there is no guarantees that these will work for your OS! On Windows open Powershell / Windows Terminal / cmd and run `./install.bat`, and on Linux / Mac open a terminal and run `./install.sh`. This should complete this installation process for you.

<br></br>

## **3. Debugging**
---

### **3.1 Python Installation Issues**
TODO: examples, discussion and bugfixes for python issues

### **3.2 PyPi (pip) Issues**
TODO: examples, discussion and bugfixes for pip issues

### **3.3 Clang Issues**
TODO: examples, discussion and bugfixes for clang issues

### **3.4 Python Script Issues**
TODO: examples, discussion and bugfixes for python script issues

### **3.5 Other Issues**
TODO: examples, discussion and bugfixes for other misc issues.

TODO: mention of bugs.md

<br></br>

## **4. Usage**
----

### **4.1. Running the Program**
TODO: Obf CLI - how to run / help / options

TODO: Obf GUI - how to run / help / options

TODO: Example Compositions

TODO: Note on first time obfuscation runtime - generating `yacctab.py`, but quick after that.

### **4.2. Supported Transformations**

TODO: Obfuscations

### **4.3. Supported Complexity Metrics**

TODO: METRICS

### **4.4. Other Notable Features**

TODO: OTHER NOTABLE FEATURES

<br></br>

## **5. Project Structure / Documentation**

### **5.1 Project Structure**

TODO: Where different parts of the project are located

### **5.2 Documentation**

TODO: Brief explanation of documentation distribution

TODO: Discussion of documentation of the AST `NodeVisitor` class.

TODO: Discussion of any supplementary documentation.

<br></br>

## **6. Testing**
----
Continuous integration with Github Action assures me that the code definitely runs on the latest Mac, Ubuntu and Windows images, but I've only been able to manually test on **Windows 11**, **Rocky Linux** and **Ubuntu** - so no guarantee there are no OS-specific issues on other systems. At the very least given that the tests pass it is likely that at least the CLI version should work on most systems.

### **6.1 Unit, Integration and System Testing**
TODO: Discussion of integration and unit tests goes here!

### **6.2 Testing Obfuscation Correctness**
TODO: Discussion of obfuscation test cases goes here!

<br></br>

## **7. Acknowledgements**
----
**[1] pycparser**, created primarily by Eli Bendersky, was used heavily in the creation of this project, providing a C source code lexer, parser and generator created using yacc, which provides an intuitive pythonic interface for generating, traversing and manipulating Abstract Syntax Trees (ASTs) of C source code programs. In addition to using the library, all files in the ***utils/fake_libc_include/*** directory are code included (and very slightly modified) from pycparser in order to allow programs using standard library headers to be modified. See: *https://github.com/eliben/pycparser*

**[2] clang** is used by pycparser to preprocess C files before it begins to parse them. See: *https://clang.llvm.org/*

**[3] JetBrains Mono** is packaged with the installation, and one of its font files is found in the ***app/graphics/fonts/Jetbrains-Mono/*** directory. This font is a clean and clear monospace font with ligature support, used to render C code in the GUI interface. See: *https://www.jetbrains.com/lp/mono/*

**[4]** **cppreference.com** was used as a source for several example C programs used as test cases for testing the code. In particular, they wer eused as they provided examples of several uncommon C features (showing edge cases and niche functionalities), providing more confidence in the program's robustness. See: *https://en.cppreference.com/w/*