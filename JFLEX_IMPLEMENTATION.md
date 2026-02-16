# JFlex Scanner Implementation Guide

## Overview
This document describes the JFlex implementation of the lexical scanner for the custom language compiler.

## Files
- `Scanner.jflex` - JFlex specification file
- `build_jflex.bat` - Windows batch script to build the scanner
- `Scanner.java` - Generated scanner class (created by JFlex)

## Prerequisites
1. **JFlex** - Lexer generator for Java
   - **Already installed at:** `C:\JFLEX`
   - Download: https://www.jflex.de/download.html
   - Minimum version: 1.6+

2. **Java Development Kit (JDK)**
   - Java 8 or higher

## Installation

**JFlex is already installed at `C:\JFLEX`**

The build scripts are configured to use this path automatically. No additional installation is needed!

## Building the Scanner

### Method 1: Using the PowerShell script (Recommended)
```powershell
cd e:\CC\CompilerConstruction
.\build.ps1 -Action build
```

### Method 2: Using the batch script (Windows)
```cmd
cd e:\CC\CompilerConstruction
build_jflex.bat
```

### Method 3: Manual compilation
```bash
cd e:\CC\CompilerConstruction\src
C:\JFLEX\bin\jflex.bat Scanner.jflex
javac -cp . *.java
```

This will generate `Scanner.java` in the same directory.

## Token Specifications

The scanner recognizes the following tokens in order of priority (longest match wins, then priority wins):

### 1. Single Line Comment (Priority 1)
- Pattern: `##` followed by any characters except newline
- Example: `## This is a comment`
- **Note**: Comments are skipped and not returned as tokens

### 2. Boolean Literal (Priority 2)
- Pattern: `true` or `false`
- Example: `true`, `false`

### 3. Identifier (Priority 3)
- Pattern: Starts with uppercase letter `[A-Z]`, followed by 0-31 lowercase letters, digits, or underscores
- Example: `MyVar`, `Count_1`, `X`
- Error: Identifier exceeding 31 characters
- Error: Identifier containing invalid characters (not [a-z0-9_] after first char)

### 4. Floating Point Literal (Priority 4)
- Pattern: Optional sign, one or more digits, decimal point, 1-6 digits
- Example: `3.14`, `+2.5`, `-0.001`
- Error: Exceeding 6 digits after decimal point
- Precision: Maximum 6 decimal places

### 5. Integer Literal (Priority 5)
- Pattern: Optional sign, one or more digits
- Example: `42`, `-15`, `+100`

### 6. Single Character Operator (Priority 6)
- Characters: `+ - * / % < > = !`
- Example: `+`, `-`, `*`

### 7. Punctuator (Priority 7)
- Characters: `( ) { } [ ] , ; :`
- Example: `;`, `{`, `}`

### 8. Invalid Identifier (Priority 8)
- Pattern: Starts with lowercase letter, followed by identifier characters
- Error: InvalidIdentifier - "Identifier must start with an uppercase letter."
- Used for better error messages

### Whitespace
- Skipped (not returned as tokens)
- Includes: space, tab, newline, carriage return

## Usage Example

```java
import java.io.*;

public class JFlexScannerDemo {
    public static void main(String[] args) throws IOException {
        // Read source code from file
        String source = new String(Files.readAllBytes(Path.of("test.lang")));
        
        // Create scanner
        Scanner scanner = new Scanner(new StringReader(source));
        
        // Scan all tokens
        List<Token> tokens = scanner.scanAllTokens();
        
        // Print tokens
        for (Token token : tokens) {
            System.out.println(token);
        }
        
        // Print statistics
        scanner.printStatistics();
        
        // Print errors if any
        ErrorHandler errors = scanner.getErrorHandler();
        if (errors.hasErrors()) {
            System.out.println("\nErrors found:");
            errors.printErrors();
        }
    }
}
```

## Comparison with ManualScanner

| Aspect | ManualScanner | JFlex Scanner |
|--------|---------------|---------------|
| Implementation | Hand-written | Auto-generated |
| Performance | Good | Better (optimized DFA) |
| Maintainability | Complex | Simple (rule-based) |
| Modification | Manual coding | Edit regex rules |
| Line/Column Tracking | Manual | Built-in |
| Token Priority | Explicit logic | Declarative order |

## Key Differences from ManualScanner

1. **Regex-based specification**: Patterns are defined using regular expressions instead of character-by-character parsing
2. **Automatic DFA generation**: JFlex generates an optimized deterministic finite automaton
3. **Simpler error handling**: Error tokens are handled more cleanly
4. **Better performance**: Generated code is typically faster than manual parsing

## Common Issues and Solutions

### Issue: "jflex: command not found"
**Solution**: Install JFlex and add it to your PATH, or use the full path to jflex executable.

### Issue: Generated Scanner.java imports are missing
**Solution**: Ensure the original Token, TokenType, SymbolTable, and ErrorHandler classes are in the same directory or in the classpath.

### Issue: Lexical errors due to token overlap
**Solution**: The JFlex specification uses longest-match rule. If patterns overlap, the longest match wins. If matches are equal length, the first rule in the specification wins.

## Testing

Test files are located in the `tests/` directory:
- `test1.lang` - Basic test
- `test2.lang` - Identifier and literal tests
- `test3.lang` - Operator and punctuator tests
- `test4.lang` - Comments and complex input
- `test5.lang` - Error cases

Compare output with `expected_test*.txt` files.

## References

- JFlex Official Documentation: https://www.jflex.de/
- JFlex Manual: https://www.jflex.de/manual.html
- Regular Expression Syntax: https://www.jflex.de/manual.html#Macros

---

**Note**: After generating Scanner.java with JFlex, compile it with:
```bash
javac -cp . Scanner.java Token.java TokenType.java SymbolTable.java ErrorHandler.java
```
