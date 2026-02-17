/* JFlex Specification for Custom Language Scanner */
import java.util.*;

%%

%public
%class Scanner
%function nextToken
%type Token
%line
%column
%standalone

%{
    private SymbolTable symbolTable = new SymbolTable();
    private ErrorHandler errorHandler = new ErrorHandler();
    private Map<TokenType, Integer> tokenCounts = new EnumMap<>(TokenType.class);
    private List<Token> allTokens = new ArrayList<>();
    
    {
        initializeTokenCounts();
    }

    private void initializeTokenCounts() {
        for (TokenType tokenType : TokenType.values()) {
            tokenCounts.put(tokenType, 0);
        }
    }

    private Token createToken(TokenType type, String lexeme) {
        Token token = new Token(type, lexeme, yyline + 1, yycolumn + 1);
        tokenCounts.put(type, tokenCounts.get(type) + 1);
        
        if (type == TokenType.IDENTIFIER) {
            symbolTable.recordIdentifier(lexeme, yyline + 1, yycolumn + 1);
        }
        
        allTokens.add(token);
        return token;
    }

    /* Helper to record error WITHOUT returning a token. 
       This allows the scanner to reset and keep going. */
    private void reportError(String errorType, String lexeme, String reason) {
        errorHandler.addError(errorType, yyline + 1, yycolumn + 1, lexeme, reason);
    }

    public List<Token> scanAllTokens() throws java.io.IOException {
        Token token;
        while ((token = nextToken()) != null) {
            // Token is already added in createToken
        }
        return Collections.unmodifiableList(allTokens);
    }

    public SymbolTable getSymbolTable() {
        return symbolTable;
    }

    public ErrorHandler getErrorHandler() {
        return errorHandler;
    }

    public Map<TokenType, Integer> getTokenCounts() {
        return Collections.unmodifiableMap(tokenCounts);
    }

    public int getTotalTokens() {
        return allTokens.size();
    }

    public void printStatistics() {
        System.out.println("Scanner Statistics:");
        System.out.println("  Total tokens: " + getTotalTokens());
        System.out.println("  Count per token type:");
        for (TokenType tokenType : TokenType.values()) {
            int count = tokenCounts.get(tokenType);
            if (count > 0) {
                System.out.println("    " + tokenType + ": " + count);
            }
        }
    }
%}

/* Regular Expressions */
WHITESPACE = [ \t\n\r]
DIGIT = [0-9]
LOWERCASE = [a-z]
UPPERCASE = [A-Z]
/* We allow uppercase in tail here so we can catch it in Java logic and report specific error */
IDENTIFIER_TAIL = [a-zA-Z0-9_]
IDENTIFIER = {UPPERCASE}{IDENTIFIER_TAIL}*

SIGN = [+\-]
EXPONENT = [eE][+-]?[0-9]+
INTEGER = {SIGN}?{DIGIT}+
/* Float Regex supporting Scientific Notation */
FLOAT = {SIGN}?{DIGIT}+\.{DIGIT}+({EXPONENT})?

SINGLE_LINE_COMMENT = ##[^\n]*
BOOLEAN_LITERAL = true|false
SINGLE_CHAR_OPERATOR = [+\-*/%<>=!]
PUNCTUATOR = [()\{\}\[\],;:]

%%

/* Token Rules in Priority Order */

/* 1. Single Line Comment */
{SINGLE_LINE_COMMENT} {
    /* Ignore comments */
}

/* 2. Boolean Literal */
{BOOLEAN_LITERAL} {
    return createToken(TokenType.BOOLEAN_LITERAL, yytext());
}

/* 3. Identifiers */
{IDENTIFIER} {
    String text = yytext();
    
    // Check 1: Length Limit
    if (text.length() > 31) {
        reportError("InvalidIdentifier", text, "Identifier exceeds maximum length of 31 characters.");
        // Do NOT return token (matches Expected output where token is missing)
    } 
    // Check 2: Uppercase in Tail (For Test 1 Match)
    // We check if the tail (substring 1) contains any uppercase letters
    else if (!text.substring(1).equals(text.substring(1).toLowerCase())) {
        reportError("InvalidIdentifier", text, "Identifier tail allows only lowercase letters, digits, or underscore.");
        // Do NOT return token (matches Expected output where token is missing)
    }
    // Valid Identifier
    else {
        return createToken(TokenType.IDENTIFIER, text);
    }
}

/* 4. Floating Point Literal */
{FLOAT} {
    String text = yytext();
    
    /* Check for precision limit (max 6 digits after dot) */
    int dotIndex = text.indexOf('.');
    int expIndex = text.toLowerCase().indexOf('e');
    int endOfDecimals = (expIndex == -1) ? text.length() : expIndex;
    int digitsAfterDot = endOfDecimals - dotIndex - 1;
    
    if (digitsAfterDot > 6) {
        reportError("MalformedLiteral", text, "Floating literal allows at most 6 digits after decimal point.");
        // Malformed floats are skipped in token stream in some tests, or added as errors. 
        // Based on Test 5, we just report error and do not return.
    } else {
        return createToken(TokenType.FLOATING_POINT_LITERAL, text);
    }
}

/* 5. Malformed Float Rules (Catch specific cases) */
{DIGIT}+\. {
    reportError("MalformedLiteral", yytext(), "Floating literal requires at least one digit after decimal point.");
}

{DIGIT}+\.{DIGIT}+\.{DIGIT}+ {
    reportError("MalformedLiteral", yytext(), "Floating literal contains multiple decimal points.");
}

{DIGIT}+\.{DIGIT}+[eE][+-]? {
    reportError("MalformedLiteral", yytext(), "Exponent part must contain at least one digit.");
}

/* 6. Integer Literal */
{INTEGER} {
    return createToken(TokenType.INTEGER_LITERAL, yytext());
}

/* 7. Operators & Punctuators */
{SINGLE_CHAR_OPERATOR} {
    return createToken(TokenType.SINGLE_CHAR_OPERATOR, yytext());
}

{PUNCTUATOR} {
    return createToken(TokenType.PUNCTUATOR, yytext());
}

/* 8. Invalid Identifier (Lowercase start) */
/* Matches things like 'trueFlag' or 'badVar' */
[a-z][a-zA-Z0-9_]* {
    reportError("InvalidIdentifier", yytext(), "Identifier must start with an uppercase letter.");
}

/* 9. Whitespace */
{WHITESPACE} {
    /* Skip */
}

/* 10. Catch-all for other invalid characters */
[^] {
    reportError("InvalidCharacter", yytext(), "Character does not start any valid token in the selected 7 token classes.");
}

<<EOF>> {
    return null;
}